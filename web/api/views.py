import logging

from cloud_snitch.models import registry
from django.http import Http404
from rest_framework import viewsets
from rest_framework import status
from rest_framework.decorators import list_route
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .decorators import cls_cached_result

from .exceptions import JobError
from .exceptions import JobRunningError

from .serializers import DiffSerializer
from .serializers import DiffNodeSerializer
from .serializers import DiffNodesSerializer
from .serializers import ModelSerializer
from .serializers import PropertySerializer
from .serializers import SearchSerializer
from .serializers import TimesChangedSerializer

from .query import Query
from .query import TimesQuery

from .tasks import objectdiff

logger = logging.getLogger(__name__)


class ModelViewSet(viewsets.ViewSet):
    """Viewset around model information."""

    def list(self, request):
        """Get a list of models."""
        models = registry.modeldicts()
        serializer = ModelSerializer(models, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Get a specific model."""
        model = registry.modeldict(pk)
        if model is None:
            raise Http404
        serializer = ModelSerializer(model)
        return Response(serializer.data)


class PathViewSet(viewsets.ViewSet):
    """Viewset around paths."""

    def list(self, request):
        """List all paths to each model."""
        paths = {}
        for label, model in registry.models.items():
            paths[label] = [l for l, _ in registry.path(label)]
        serializer = ModelSerializer(paths)
        return Response(serializer.data)


class PropertyViewSet(viewsets.ViewSet):
    """Viewset around model properties."""

    def list(self, request, model=None):
        """List all properties models."""
        props = registry.properties()
        serializer = PropertySerializer(props)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """List all properties for a specific model."""
        props = registry.properties(model=pk)
        if not props:
            raise Http404
        serializer = PropertySerializer(props)
        return Response(serializer.data)


class ObjectViewSet(viewsets.ViewSet):
    """View set for searching, viewing objects."""

    @cls_cached_result(prefix="times", timeout=3600)
    def _times(self, model, identity):
        """Get times a specific instance of a model has changed.

        :param model: Name of the model
        :type model: str
        :param identity: Identity of the instance
        :type identity: str
        :returns: List of times the instance has changed.
        :rtype: list
        """
        # Build query to get times
        query = TimesQuery(model, identity)
        times = query.fetch()
        return times

    @list_route(methods=['post'])
    def times(self, request):
        """Get times an object has changed.

        The object's created_at time will be added if not present.
        """
        # Validate input
        times = TimesChangedSerializer(data=request.data)
        if not times.is_valid():
            raise ValidationError(times.errors)
        vd = times.validated_data

        # Find object by type and identity
        query = Query(vd.get('model')) \
            .identity(vd.get('identity')) \
            .time(vd.get('time'))

        records = query.fetch()

        # Raise 404 if not found
        if not records:
            raise Http404()

        created_at = records[0][vd.get('model')]['created_at']

        # Build query to get times
        logger.debug("GETTING TIMES")
        times = self._times(vd['model'], vd['identity'])

        if created_at not in times:
            times.append(created_at)

        results = ModelSerializer({
            'data': vd,
            'times': times
        })
        return Response(results.data)

    @list_route(methods=['post'])
    def search(self, request):
        """Search objects by type, identity, and property filters."""
        search = SearchSerializer(data=request.data)
        if not search.is_valid():
            raise ValidationError(search.errors)

        vd = search.validated_data
        query = Query(vd.get('model')) \
            .identity(vd.get('identity')) \
            .time(vd.get('time'))

        for f in vd.get('filters', []):
            query.filter(
                f['prop'],
                f['operator'],
                f['value'],
                label=f['model']
            )

        for o in vd.get('orders', []):
            query.orderby(o['prop'], o['direction'], label=o['model'])

        count = query.count()

        records = query.page(
            page=vd['page'],
            pagesize=vd['pagesize'],
            index=vd.get('index')
        )

        serializer = ModelSerializer({
            'query': str(query),
            'data': vd,
            'params': query.params,
            'count': count,
            'pagesize': vd['pagesize'],
            'page': vd['page'],
            'records': records
        })
        return Response(serializer.data)


class ObjectDiffViewSet(viewsets.ViewSet):
    """Viewset for diffing the same object at different points in time."""

    def _data(self, request, serializer):
        """Serialize input from request and validate.

        :param request: Http request
        :type request: ?
        :param serializer: Serializer class to use.
        :type serializer: rest_framework.serializers.Serializer
        :returns: Validated data
        :rtype: dict
        """
        s = serializer(data=request.data)
        if not s.is_valid():
            raise ValidationError(s.errors)
        return s.validated_data

    def _exists(self, model, identity, time):
        """Check that an instance of a model exists at a time.

        :param model: Name of the model
        :type model: str
        :param identity: Identity of the instance of the model.
        :type identity: str
        :param time: Time to verify in milliseconds since epoch
        :type type: int
        """
        query = Query(model).identity(identity).time(time)
        records = query.fetch()
        logger.debug("Found {} matches for time {}".format(len(records), time))
        return len(records) > 0

    def _check_sides(self, data):
        """Check both sides of diff for existence.

        :param data: Validate request data
        :type data: dict
        """
        # Find left side
        exists = self._exists(
            data.get('model'),
            data.get('identity'),
            data.get('left_time')
        )
        if not exists:
            raise Http404("Left not found")

        # Find right side
        exists = self._exists(
            data.get('model'),
            data.get('identity'),
            data.get('right_time')
        )
        if not exists:
            raise Http404("Right not found")

    def _job_running_response(self):
        """Create a response for a diff that is still running.

        :returns: Response with http 202 status code.
        :rtype: rest_framework.response.Response
        """
        return Response(
            {'status': 'Job is running. Try later.'},
            status=status.HTTP_202_ACCEPTED
        )

    def _job_error_response(self):
        """Create a response for a diff that has failed.

        :returns: Response with 500 status code.
        :rtype: rest_framework.response.Response
        """
        return Response(
            {'status': 'The job failed.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    @list_route(methods=['post'])
    def node(self, request):
        """Get a specific node in the diff tree."""
        # Validate request
        data = self._data(request, DiffNodeSerializer)

        # Make sure both sides are kosher
        self._check_sides(data)
        try:
            diff = objectdiff(
                data['model'],
                data['identity'],
                data['left_time'],
                data['right_time']
            )
        except JobRunningError:
            return self._job_running_response()
        except JobError:
            return self._job_error_response()

        # 404 if node not found.
        node = diff.getnode(data['node_model'], data['node_identity'])
        if node is None:
            raise Http404()

        results = ModelSerializer({
            'node': node,
            'nodecount': diff.diffdict['nodecount'],
            'data': data
        })
        return Response(results.data)

    @list_route(methods=['post'])
    def nodes(self, request):
        """Get a range of nodes from the diff tree."""
        # Validate request
        data = self._data(request, DiffNodesSerializer)

        # Make sure both sides are kosher
        self._check_sides(data)

        try:
            diff = objectdiff(
                data['model'],
                data['identity'],
                data['left_time'],
                data['right_time']
            )
        except JobRunningError:
            return self._job_running_response()
        except JobError:
            return self._job_error_response()

        results = ModelSerializer({
            'nodes': diff.getnodes(data['offset'], data['limit']),
            'nodecount': diff.diffdict['nodecount'],
            'data': data
        })
        return Response(results.data)

    @list_route(methods=['post'])
    def structure(self, request):
        """Get structure of the tree."""
        # Validate the data
        data = self._data(request, DiffSerializer)

        # Make sure both sides are kosher
        self._check_sides(data)

        try:
            diff = objectdiff(
                data['model'],
                data['identity'],
                data['left_time'],
                data['right_time']
            )
        except JobRunningError:
            return self._job_running_response()
        except JobError:
            return self._job_error_response()

        # Return the response
        results = ModelSerializer({
            'frame': diff.frame(),
            'nodemap': diff.diffdict['nodemap'],
            'nodecount': diff.diffdict['nodecount'],
            'data': data
        })
        return Response(results.data)
