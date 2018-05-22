import logging

from django.test import TestCase

from api.serializers import DiffNodeSerializer
from api.serializers import DiffNodesSerializer
from api.serializers import DiffSerializer
from api.serializers import FilterSerializer
from api.serializers import ModelSerializer
from api.serializers import OrderSerializer
from api.serializers import PropertySerializer
from api.serializers import SearchSerializer
from api.serializers import TimesChangedSerializer

logging.getLogger('api').setLevel(logging.ERROR)


class TestModelSerializer(TestCase):

    def test_serialize_single(self):
        test_obj = {'somekey': 'someval'}
        s = ModelSerializer(test_obj)
        data = s.data
        self.assertTrue(data is test_obj)

    def test_serialize_many(self):
        test_objs = [
            {'somekey1': 'someval1'},
            {'somekey2': 'someval2'}
        ]
        data = ModelSerializer(test_objs, many=True).data
        for i, obj in enumerate(test_objs):
            self.assertTrue(obj is data[i])


class TestPropertySerializer(TestCase):

    def test_serialize_single(self):
        props = ['prop1', 'prop2', 'prop3']
        data = PropertySerializer(props).data
        self.assertTrue(props is data['properties'])


class SerializerCase(TestCase):
    """Base Class for testing deserialization."""

    def deserialize(self):
        self.serializer = self.serializer_class(data=self.data)

    def assertValid(self):
        self.deserialize()
        self.assertTrue(self.serializer.is_valid())

    def assertInvalid(self):
        self.deserialize()
        self.assertFalse(self.serializer.is_valid())


class TestFilterSerializer(SerializerCase):

    serializer_class = FilterSerializer

    def setUp(self):
        self.data = {
            'model': 'Environment',
            'prop': ' account_number',
            'operator': '=',
            'value': 'test_val'
        }

    def test_valid(self):
        self.assertValid()

    def test_invalid_model(self):
        self.data['model'] = 'somerandommodel'
        self.assertInvalid()

    def test_missing_model(self):
        del self.data['model']
        self.assertInvalid()

    def test_property_too_long(self):
        self.data['prop'] = 't' * 300
        self.assertInvalid()

    def test_property_missing(self):
        del self.data['prop']
        self.assertInvalid()

    def test_invalid_operator(self):
        self.data['operator'] = 'abc'
        self.assertInvalid()

    def test_missing_operator(self):
        del self.data['operator']
        self.assertInvalid()

    def test_value_too_long(self):
        self.data['value'] = 't' * 257
        self.assertInvalid()

    def test_missing_value(self):
        del self.data['value']
        self.assertInvalid()


class TestOrderSerializer(SerializerCase):

    serializer_class = OrderSerializer

    def setUp(self):
        self.data = {
            'model': 'Environment',
            'prop': 'account_number',
            'direction': 'asc'
        }

    def test_valid(self):
        self.assertValid()

    def test_invalid_model(self):
        self.data['model'] = 'somerandommodel'
        self.assertInvalid()

    def test_missing_model(self):
        del self.data['model']
        self.assertInvalid()

    def test_invalid_prop(self):
        self.data['prop'] = '    a      b '
        self.assertInvalid()

    def test_missing_prop(self):
        del self.data['prop']
        self.assertInvalid()

    def test_invalid_direction(self):
        self.data['direction'] = 'dasc'
        self.assertInvalid()

    def test_missing_direction(self):
        del self.data['direction']
        self.assertInvalid()


class TestSearchSerializer(SerializerCase):

    serializer_class = SearchSerializer

    def setUp(self):
        self.data = {
            'model': 'Environment',
            'time': 1,
            'identity': 'someid',
            'filters': [{
                'model': 'Environment',
                'prop': 'account_number',
                'operator': '=',
                'value': 'someval'
            }],
            'orders': [{
                'model': 'Environment',
                'prop': 'account_number',
                'direction': 'asc'
            }],
            'page': 2,
            'pagesize': 10,
            'index': 15
        }

    def test_valid(self):
        self.assertValid()

    def test_missing_model(self):
        del self.data['model']
        self.assertInvalid()

    def test_invalid_model(self):
        self.data['model'] = 'somerandommodel'
        self.assertInvalid()

    def test_negative_time(self):
        self.data['time'] = -1
        self.assertInvalid()

    def test_missing_time(self):
        """Test time not provided. Should be valid."""
        del self.data['time']
        self.assertValid()

    def test_identity_too_long(self):
        self.data['identity'] = 't' * 257
        self.assertInvalid()

    def test_missing_identity(self):
        """Test identity not provided. Should be valid."""
        del self.data['identity']
        self.assertValid()

    def test_missing_filters(self):
        """Test without filters. Should be valid."""
        del self.data['filters']
        self.assertValid()

    def test_nonlist_filters(self):
        self.data['filters'] = 'afilter'
        self.assertInvalid()

    def test_emptylist_filters(self):
        self.data['filters'] = []
        self.assertValid()

    def test_filters_with_invalid_prop(self):
        self.data['filters'] = [{
            'model': 'Environment',
            'prop': 'somerandomprop',
            'operator': '=',
            'value': 'someval'
        }]
        self.assertInvalid()

    def test_missing_orders(self):
        del self.data['orders']
        self.assertValid()

    def test_emptylist_orders(self):
        self.data['orders'] = []
        self.assertValid()

    def test_nonlist_orders(self):
        self.data['orders'] = 'anorder'
        self.assertInvalid()

    def test_orders_with_invalid_prop(self):
        self.data['orders'] = [{
            'model': 'Environment',
            'prop': 'somerandomprop',
            'order': 'asc'
        }]
        self.assertInvalid()

    def test_missing_page(self):
        del self.data['page']
        self.assertValid()
        self.assertEquals(self.serializer.validated_data['page'], 1)

    def test_invalid_page(self):
        self.data['page'] = -1
        self.assertInvalid()

    def test_missing_pagesize(self):
        del self.data['pagesize']
        self.assertValid()
        self.assertEquals(self.serializer.validated_data['pagesize'], 500)

    def test_missing_index(self):
        del self.data['index']
        self.assertValid()

    def test_invalid_index(self):
        self.data['index'] = -1
        self.assertInvalid()


class TestTimesChangedSerializer(SerializerCase):

    serializer_class = TimesChangedSerializer

    def setUp(self):
        self.data = {
            'model': 'Environment',
            'identity': 'someid',
            'time': 1
        }

    def test_valid(self):
        self.assertValid()

    def test_missing_model(self):
        del self.data['model']
        self.assertInvalid()

    def test_invalid_model(self):
        self.data['model'] = 'somerandommodel'
        self.assertInvalid()

    def test_missing_identity(self):
        del self.data['identity']
        self.assertInvalid()

    def test_identity_too_long(self):
        self.data['identity'] = 't' * 257
        self.assertInvalid()

    def test_missing_time(self):
        del self.data['time']
        self.assertValid()

    def test_invalid_time(self):
        self.data['time'] = -1
        self.assertInvalid()


class TestDiffSerializer(SerializerCase):

    serializer_class = DiffSerializer

    def setUp(self):
        self.data = {
            'model': 'Environment',
            'identity': 'someid',
            'left_time': 10,
            'right_time': 20
        }

    def test_valid(self):
        self.assertValid()

    def test_missing_model(self):
        del self.data['model']
        self.assertInvalid()

    def test_invalid_model(self):
        self.data['model'] = 'somerandommodel'
        self.assertInvalid()

    def test_missing_identity(self):
        del self.data['identity']
        self.assertInvalid()

    def test_identity_too_long(self):
        self.data['identity'] = 't' * 257
        self.assertInvalid()

    def test_missing_left_time(self):
        del self.data['left_time']
        self.assertInvalid()

    def test_invalid_left_time(self):
        self.data['left_time'] = -1
        self.assertInvalid()

    def test_missing_right_time(self):
        del self.data['right_time']
        self.assertInvalid()

    def test_invalid_right_time(self):
        self.data['right_time'] = -1
        self.assertInvalid()


class TestDiffNodesSerializer(SerializerCase):

    serializer_class = DiffNodesSerializer

    def setUp(self):
        self.data = {
            'model': 'Environment',
            'identity': 'someid',
            'left_time': 10,
            'right_time': 20,
            'offset': 0,
            'limit': 5
        }

    def test_valid(self):
        self.assertValid()

    def test_missing_model(self):
        del self.data['model']
        self.assertInvalid()

    def test_invalid_model(self):
        self.data['model'] = 'somerandommodel'
        self.assertInvalid()

    def test_missing_identity(self):
        del self.data['identity']
        self.assertInvalid()

    def test_identity_too_long(self):
        self.data['identity'] = 't' * 257
        self.assertInvalid()

    def test_missing_left_time(self):
        del self.data['left_time']
        self.assertInvalid()

    def test_invalid_left_time(self):
        self.data['left_time'] = -1
        self.assertInvalid()

    def test_missing_right_time(self):
        del self.data['right_time']
        self.assertInvalid()

    def test_invalid_right_time(self):
        self.data['right_time'] = -1
        self.assertInvalid()

    def test_missing_offset(self):
        del self.data['offset']
        self.assertInvalid()

    def test_invalid_offset(self):
        self.data['offset'] = -1
        self.assertInvalid()

        self.data['offset'] = 'somenonnumber'
        self.assertInvalid()

    def test_missing_limit(self):
        del self.data['limit']
        self.assertInvalid()

    def test_invalid_limit(self):
        self.data['limit'] = -1
        self.assertInvalid()

        self.data['limit'] = 'somenonnumber'
        self.assertInvalid()


class TestDiffNodeSerializer(SerializerCase):

    serializer_class = DiffNodeSerializer

    def setUp(self):
        self.data = {
            'model': 'Environment',
            'identity': 'someid',
            'left_time': 10,
            'right_time': 20,
            'node_model': 'Environment',
            'node_identity': 'someid'
        }

    def test_valid(self):
        self.assertValid()

    def test_missing_model(self):
        del self.data['model']
        self.assertInvalid()

    def test_invalid_model(self):
        self.data['model'] = 'somerandommodel'
        self.assertInvalid()

    def test_missing_identity(self):
        del self.data['identity']
        self.assertInvalid()

    def test_identity_too_long(self):
        self.data['identity'] = 't' * 257
        self.assertInvalid()

    def test_missing_left_time(self):
        del self.data['left_time']
        self.assertInvalid()

    def test_invalid_left_time(self):
        self.data['left_time'] = -1
        self.assertInvalid()

    def test_missing_right_time(self):
        del self.data['right_time']
        self.assertInvalid()

    def test_invalid_right_time(self):
        self.data['right_time'] = -1
        self.assertInvalid()

    def test_missing_node_model(self):
        del self.data['node_model']
        self.assertInvalid()

    def test_invalid_node_model(self):
        self.data['node_model'] = 'somerandommodel'
        self.assertInvalid()

    def test_missing_node_identity(self):
        del self.data['node_model']
        self.assertInvalid()

    def test_node_identity_too_long(self):
        self.data['node_identity'] = 't' * 257
        self.assertInvalid()
