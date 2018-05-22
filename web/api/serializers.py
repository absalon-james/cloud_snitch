import logging

from cloud_snitch.models import registry
from rest_framework.serializers import BaseSerializer
from rest_framework.serializers import Serializer
from rest_framework.serializers import ChoiceField
from rest_framework.serializers import CharField
from rest_framework.serializers import IntegerField
from rest_framework.serializers import ListField
from rest_framework.serializers import SlugField

from rest_framework.serializers import ValidationError


logger = logging.getLogger(__name__)

_operators = [
    '=',
    '<>',
    '>',
    '>=',
    '<',
    '<=',
    'CONTAINS',
    'STARTS WITH',
    'ENDS WITH'
]


class ModelSerializer(BaseSerializer):
    """Debug serializer for dicts"""
    def to_representation(self, obj):
        """Get dict repr

        :param obj: Dict to represent
        :type obj: dict
        :returns: Dict representation
        :rtype: dict
        """
        return obj


class PropertySerializer(BaseSerializer):
    """Serializer for list of properties."""
    def to_representation(self, obj):
        """Dict representation.

        :param obj: List of properties
        :type obj: list
        :returns: Dict representation
        :rtype dict
        """
        return dict(properties=obj)


class FilterSerializer(Serializer):
    """Serializer for filters on a query"""
    model = ChoiceField([m.label for m in registry.models.values()])
    prop = SlugField(max_length=256, required=True)
    operator = ChoiceField(_operators, required=True)
    value = CharField(max_length=256, required=True)


class OrderSerializer(Serializer):
    """Serializer for order by on a query."""
    model = ChoiceField([m.label for m in registry.models.values()])
    prop = SlugField(max_length=256, required=True)
    direction = ChoiceField(['asc', 'desc'])


class SearchSerializer(Serializer):
    """Serializer for search queries."""
    model = ChoiceField([m.label for m in registry.models.values()])
    time = IntegerField(min_value=0, required=False)
    identity = CharField(max_length=256, required=False)
    filters = ListField(child=FilterSerializer(), required=False)
    orders = ListField(child=OrderSerializer(), required=False)

    page = IntegerField(min_value=0, required=False, default=1)
    pagesize = IntegerField(min_value=1, required=False, default=500)
    index = IntegerField(min_value=0, required=False)

    def validate(self, data):
        model_set = set([t[0] for t in registry.path(data['model'])])
        model_set.add(data['model'])

        for f in data.get('filters', []):
            # Make sure filter model is in path of search model
            if f['model'] not in model_set:
                raise ValidationError(
                    'Model {} not in path of {}'
                    .format(f['model'], data['model'])
                )

            # Make sure filter property is property of filter model
            if f['prop'] not in registry.properties(f['model']):
                raise ValidationError(
                    'Model {} does not have property {}'.format(
                        f['model'],
                        f['prop']
                    )
                )

        for o in data.get('orders', []):
            # Make sure order model is in path of search model
            if o['model'] not in model_set:
                raise ValidationError(
                    'Model {} not in path of {}'
                    .format(o['model'], data['model'])
                )

            # Make sure order property is property of order model
            if o['prop'] not in registry.properties(o['model']):
                raise ValidationError(
                    'Model {} does not have property {}'.format(
                        o['model'],
                        o['prop']
                    )
                )

        return data


class TimesChangedSerializer(Serializer):
    """Serializer for detailed query of one object."""
    model = ChoiceField([m.label for m in registry.models.values()])
    identity = CharField(max_length=256, required=True)
    time = IntegerField(min_value=0, required=False)


class DiffSerializer(Serializer):
    """Serializer for requesting diff structure."""
    model = ChoiceField([m.label for m in registry.models.values()])
    identity = CharField(max_length=256, required=True)
    left_time = IntegerField(min_value=0, required=True)
    right_time = IntegerField(min_value=0, required=True)


class DiffNodesSerializer(Serializer):
    """Serializer for requesting a range of nodes from an offset."""
    model = ChoiceField([m.label for m in registry.models.values()])
    identity = CharField(max_length=256, required=True)
    left_time = IntegerField(min_value=0, required=True)
    right_time = IntegerField(min_value=0, required=True)
    offset = IntegerField(min_value=0, required=True)
    limit = IntegerField(min_value=1, required=True)


class DiffNodeSerializer(Serializer):
    """Serializer for requesting a specific node."""
    model = ChoiceField([m.label for m in registry.models.values()])
    identity = CharField(max_length=256, required=True)
    left_time = IntegerField(min_value=0, required=True)
    right_time = IntegerField(min_value=0, required=True)
    node_model = ChoiceField([m.label for m in registry.models.values()])
    node_identity = CharField(max_length=256, required=True)
