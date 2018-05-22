import mock

from django.test import TestCase

from api.query import Query
from api.query import TimesQuery

from api.exceptions import InvalidLabelError
from api.exceptions import InvalidPropertyError


class FakeRecords(list):

    def single(self):
        return self[0]


class FakeDataset:

    def __init__(self, data):
        self.data = data
        self.count = 0

    def get_data(self):
        res = self.data[self.count]
        self.count += 1
        return res


class FakeTransaction:

    def __init__(self, data):
        self.data = data

    def begin_transaction(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def run(self, query, **params):
        return self.data.get_data()


class FakeSession:

    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return FakeTransaction(self.data)

    def __exit__(self, *args):
        pass


class FakeConnection:

    def __init__(self, data):
        self.data = FakeDataset(data)

    def session(self):
        return FakeSession(self.data)


class TestQuery(TestCase):
    """
    RETURN environment
    ORDER BY environment.account_number_name ASC
    """

    def test_match_root_label(self):
        """Test match clause targeted at a root level model."""
        q = Query('Environment')
        expected = "MATCH (environment:Environment)"
        self.assertTrue(expected in str(q))

    def test_match_with_state(self):
        """Test match clause including a model with state."""
        q = Query('Host')
        expected = (
            "MATCH (environment:Environment)-[r0:HAS_HOST]->(host:Host) "
            "\nMATCH (host)-[r_host_state:HAS_STATE]->(host_state:HostState)"
        )
        self.assertTrue(expected in str(q))

    def test_return_root_label(self):
        """Test return clause targeted at a root level model."""
        q = Query('Environment')
        expected = "RETURN environment"
        self.assertTrue(expected in str(q))

    def test_return_with_state(self):
        """Test return clause that should include state."""
        q = Query('Host')
        expected = 'RETURN environment, host, host_state'
        self.assertTrue(expected in str(q))

    @mock.patch('api.query.utils.milliseconds_now', return_value=10)
    def test_default_time(self, m_now):
        """Test that default time parameter."""
        q = Query('Environment')
        self.assertEquals(q.params['time'], 10)
        q = Query('Environment')
        q.time(None)
        self.assertEquals(q.params['time'], 10)

    def test_provided_time(self):
        """Test that providing a time changes the query params."""
        q = Query('Environment')
        q.time(3)
        self.assertEquals(q.params['time'], 3)

    def test_orderby_default(self):
        """Test default orderby clause."""
        q = Query('Environment')
        expected = "ORDER BY environment.account_number_name ASC"
        self.assertTrue(expected in str(q))

    def test_orderby_no_label(self):
        """Test a single nondefault orderby"""
        q = Query('Environment')
        q.orderby('account_number', 'DESC')
        expected = "ORDER BY environment.account_number DESC"
        self.assertTrue(expected in str(q))

    def test_orderby_invalid_property(self):
        """Test that orderby raises InvalidPropertyError"""
        q = Query('Environment')
        with self.assertRaises(InvalidPropertyError):
            q.orderby('invalidproperty', 'ASC')

    def test_orderby_invalid_label(self):
        """Test that orderby raises InvalidLabelError"""
        q = Query('Environment')
        with self.assertRaises(InvalidLabelError):
            q.orderby('aproperty', 'DESC', label='invalidlabel')

    def test_orderby_multiple(self):
        """Test multiple orderby statements."""
        q = Query('Environment')
        q.orderby('account_number', 'ASC', label='Environment')
        q.orderby('name', 'DESC', label='Environment')
        expected = (
            "ORDER BY environment.account_number ASC, "
            "environment.name DESC"
        )
        self.assertTrue(expected in str(q))

    def test_orderby_state_property(self):
        """Test orderby on a state property."""
        q = Query('Host')
        q.orderby('kernel', 'DESC', label='Host')
        expected = 'ORDER BY host_state.kernel DESC'
        self.assertTrue(expected in str(q))

    def test_limit_none(self):
        """Test query where no limit has been set."""
        q = Query('Environment')
        self.assertFalse('LIMIT' in str(q))

    def test_limit(self):
        """Test query where a limit as been set."""
        q = Query('Environment')
        q.limit(5)
        q.limit(10)
        self.assertTrue('LIMIT 10' in str(q))

    def test_skip_none(self):
        """Test query where no skip has been set."""
        q = Query('Environment')
        self.assertFalse('SKIP' in str(q))

    def test_skip(self):
        """Test query where skip has been set."""
        q = Query('Environment')
        q.skip(5)
        q.skip(10)
        self.assertTrue('SKIP 10' in str(q))

    def test_filter_without_label(self):
        """Test filtering using default label."""
        q = Query('Host')
        q.filter('hostname', '=', 'somehostname')
        expected = 'WHERE host.hostname = $filterval0'
        self.assertTrue(expected in str(q))
        self.assertEquals(q.params['filterval0'], 'somehostname')

    def test_filter_with_label(self):
        """Test filtering with a non default label."""
        q = Query('Host')
        q.filter('account_number', '=', 'somenumber', label='Environment')
        expected = 'WHERE environment.account_number = $filterval0'
        self.assertTrue(expected in str(q))

    def test_filter_invalid_label(self):
        """Test filtering with invalid label."""
        q = Query('Host')
        with self.assertRaises(InvalidLabelError):
            q.filter('someprop', 'someop', 'someval', label='InvalidLabel')

    def test_filter_invalid_prop(self):
        """Test filtering with invalid property."""
        q = Query('Host')
        with self.assertRaises(InvalidPropertyError):
            q.filter('someinvalidprop', 'someop', 'someval')

    def test_multiple_filters(self):
        """Tests more than one filters."""
        q = Query('Host')
        q.filter('hostname', '=', 'somehostname')
        q.filter('kernel', '=', 'somekernel')
        expected = (
            'WHERE host.hostname = $filterval0 AND '
            'host_state.kernel = $filterval1'
        )
        self.assertTrue(expected in str(q))

    def test_rel_filters(self):
        """Test adding time filters on relationships."""
        q = Query('Virtualenv')
        expected = (
            "r0.from <= $time < r0.to AND r1.from <= $time < r1.to "
            "AND r_host_state.from <= $time < r_host_state.to"
        )
        self.assertTrue(expected in str(q))

    @mock.patch('api.query.get_connection')
    def test_count(self, m_connection):
        """Tests counting number of results."""
        data = FakeRecords()
        data.append({'total': 13})
        data = [data]
        m_connection.return_value = FakeConnection(data)
        q = Query('Environment')
        self.assertEquals(q.count(), 13)

    @mock.patch('api.query.Query.fetch')
    def test_page_defaults(self, m_fetch):
        """Test default arguments to page() method."""
        q = Query('Environment')
        q.page()

        expected = 'SKIP 0'
        self.assertTrue(expected in str(q))
        expected = 'LIMIT 100'
        self.assertTrue(expected in str(q))

    @mock.patch('api.query.get_connection')
    def test_page_with_page(self, m_fetch):
        """Test providing page with a page and a size."""
        q = Query('Environment')
        q.page(page=3, pagesize=500)
        expected = "SKIP 1000"
        self.assertTrue(expected in str(q))
        expected = "LIMIT 500"
        self.assertTrue(expected in str(q))

    @mock.patch('api.query.get_connection')
    def test_page_with_index(self, m_fetch):
        """Test providing page an index and a size."""
        q = Query('Environment')
        q.page(index=3, pagesize=500)
        expected = "SKIP 2"
        self.assertTrue(expected in str(q))
        expected = "LIMIT 500"
        self.assertTrue(expected in str(q))

    @mock.patch('api.query.get_connection')
    def test_page_with_negative_index(self, m_fetch):
        """Test providing page with a negative index and a size."""
        q = Query('Environment')
        q.page(index=-10, pagesize=500)
        expected = "SKIP 0"
        self.assertTrue(expected in str(q))
        expected = "LIMIT 500"
        self.assertTrue(expected in str(q))


class TestTimesQuery(TestCase):

    def test_query_str_and_params(self):
        label = 'Environment'
        id_ = 'someid'
        expected = (
            "MATCH p = (environment:Environment)-[*]->(other)"
            "\nWHERE environment.account_number_name = $identity"
            "\nWITH relationships(p) as rels"
            "\nUNWIND rels as r"
            "\nreturn DISTINCT r.from as t"
            "\nORDER BY t DESC"
        )
        q = TimesQuery(label, id_)
        self.assertEquals(str(q), expected)
        self.assertEquals(q.params['identity'], id_)

    @mock.patch('api.query.get_connection')
    def test_fetch(self, m_connection):
        data = [[{'t': 1}, {'t': 2}, {'t': 3}]]
        m_connection.return_value = FakeConnection(data)
        q = TimesQuery('Environment', 'someid')
        self.assertListEqual([1, 2, 3], q.fetch())

        data = [[]]
        m_connection.return_value = FakeConnection(data)
        self.assertListEqual([], q.fetch())
