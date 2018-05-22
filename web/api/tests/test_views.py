import logging
import mock

from django.contrib.auth.models import User

from rest_framework import status
from rest_framework.test import APITestCase

from api.exceptions import JobError
from api.exceptions import JobRunningError

logging.getLogger('neo4j').setLevel(logging.ERROR)
logging.getLogger('api').setLevel(logging.ERROR)
logging.getLogger('api.query').setLevel(logging.ERROR)
logging.getLogger('django').setLevel(logging.ERROR)


class BaseApiTestCase(APITestCase):

    credentials = {
        'username': 'testuser',
        'password': 'testpassword'
    }

    def setUp(self):
        User.objects.create_user(
            self.credentials['username'],
            password=self.credentials['password']
        )
        self.client.logout()


class TestModelViewSetList(BaseApiTestCase):

    def test_without_auth(self):
        resp = self.client.get('/api/models/')
        self.assertEquals(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_with_auth(self):
        self.client.login(**self.credentials)
        resp = self.client.get('/api/models/')
        self.assertEquals(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertTrue(isinstance(data, list))


class TestModelViewSetRetrieve(BaseApiTestCase):

    def test_without_auth(self):
        resp = self.client.get('/api/models/Environment/')
        self.assertEquals(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_found(self):
        self.client.login(**self.credentials)
        resp = self.client.get('/api/models/SomeRandomModel/')
        self.assertEquals(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_200(self):
        self.client.login(**self.credentials)
        resp = self.client.get('/api/models/Environment/')
        self.assertEquals(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertTrue(isinstance(data, dict))


class TestPathViewSetList(BaseApiTestCase):
    def test_without_auth(self):
        resp = self.client.get('/api/paths/')
        self.assertEquals(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_with_auth(self):
        self.client.login(**self.credentials)
        resp = self.client.get('/api/paths/')
        self.assertEquals(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertTrue(isinstance(data, dict))
        for label, path in data.items():
            self.assertTrue(isinstance(path, list))
            self.assertTrue(isinstance(label, str))


class TestPropertyViewSetList(BaseApiTestCase):
    def test_without_auth(self):
        resp = self.client.get('/api/properties/')
        self.assertEquals(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_with_auth(self):
        self.client.login(**self.credentials)
        resp = self.client.get('/api/properties/')
        self.assertEquals(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertTrue(isinstance(data, dict))
        self.assertTrue(isinstance(data['properties'], list))


class TestObjectViewSetTimes(BaseApiTestCase):

    fake_fetch_result = [{
        'Environment': {
            'created_at': 10
        }
    }]

    def setUp(self):
        super(TestObjectViewSetTimes, self).setUp()
        self.body = {
            'model': 'Environment',
            'identity': 'someid',
            'time': 10
        }

    def test_without_auth(self):
        resp = self.client.post('/api/objects/times/', self.body)
        self.assertEquals(resp.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch('api.query.Query.fetch', return_value=None)
    def test_not_found(self, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post('/api/objects/times/', self.body)
        self.assertEquals(resp.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('api.query.Query.fetch', return_value=fake_fetch_result)
    @mock.patch('api.query.TimesQuery.fetch', return_value=[1, 2, 3])
    def test_resp(self, m_fetch, m_times):
        self.client.login(**self.credentials)
        resp = self.client.post('/api/objects/times/', self.body)
        data = resp.json()
        self.assertDictEqual(self.body, data['data'])
        self.assertListEqual([1, 2, 3, 10], data['times'])

    def test_invalid(self):
        self.client.login(**self.credentials)
        resp = self.client.post('/api/objects/times/', {})
        self.assertEquals(resp.status_code, status.HTTP_400_BAD_REQUEST)


class TestObjectViewSetSearch(BaseApiTestCase):

    def setUp(self):
        super(TestObjectViewSetSearch, self).setUp()
        self.body = {
            'model': 'Environment',
            'pagesize': 500,
            'page': 1
        }

    def test_no_auth(self):
        resp = self.client.post('/api/objects/search/', self.body)
        self.assertEquals(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_req(self):
        self.client.login(**self.credentials)
        resp = self.client.post('/api/objects/search/', {})
        self.assertEquals(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('api.query.Query.count', return_value=5)
    @mock.patch('api.query.Query.page', return_value='testpage')
    def test_resp(self, m_page, m_count):
        self.maxDiff = None
        self.client.login(**self.credentials)
        resp = self.client.post('/api/objects/search/', self.body)
        data = resp.json()

        self.assertTrue('data' in data)
        self.assertTrue(isinstance(data['data'], dict))
        self.assertTrue('query' in data)
        self.assertTrue(isinstance(data['query'], str))
        self.assertTrue('params' in data)
        self.assertTrue(isinstance(data['params'], dict))
        self.assertTrue('count' in data)
        self.assertEquals(data['count'], 5)
        self.assertTrue('pagesize' in data)
        self.assertEquals(data['pagesize'], 500)
        self.assertTrue('page' in data)
        self.assertEquals(data['page'], 1)
        self.assertTrue('records' in data)
        self.assertEquals(data['records'], 'testpage')


class FakeDiffResult:

    def __init__(self, find_node=True):
        self.find_node = find_node
        self.diffdict = {'nodecount': 5, 'nodemap': 'nodemap'}

    def frame(self):
        return 'frame'

    def getnode(self, model, identity):
        return 'node' if self.find_node else None

    def getnodes(self, offset, limit):
        return [1, 2, 3]


class TestObjectDiffViewSetNode(BaseApiTestCase):

    baseurl = '/api/objectdiffs/node/'

    def setUp(self):
        super(TestObjectDiffViewSetNode, self).setUp()
        self.body = {
            'model': 'Environment',
            'identity': 'someid',
            'left_time': 1,
            'right_time': 2,
            'node_model': 'Environment',
            'node_identity': 'someid'
        }

    def test_without_auth(self):
        resp = self.client.post(self.baseurl, {})
        self.assertEquals(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_req(self):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, {})
        self.assertEquals(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('api.query.Query.fetch', return_value=[])
    def test_left_not_found(self, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, self.body)
        self.assertEquals(resp.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('api.query.Query.fetch', side_effect=[[], [1]])
    def test_right_not_found(self, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, self.body)
        self.assertEquals(resp.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('api.query.Query.fetch', side_effect=[[1], [1]])
    @mock.patch('api.views.objectdiff', side_effect=JobRunningError())
    def test_job_running(self, m_diff, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, self.body)
        self.assertEquals(resp.status_code, status.HTTP_202_ACCEPTED)

    @mock.patch('api.query.Query.fetch', side_effect=[[1], [1]])
    @mock.patch(
        'api.views.objectdiff',
        return_value=FakeDiffResult(find_node=False)
    )
    def test_node_not_found(self, m_diff, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, self.body)
        self.assertEquals(resp.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('api.query.Query.fetch', side_effect=[[1], [1]])
    @mock.patch('api.views.objectdiff', side_effect=JobError())
    def test_job_error(self, m_diff, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, self.body)
        self.assertEquals(
            resp.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    @mock.patch('api.query.Query.fetch', side_effect=[[1], [1]])
    @mock.patch(
        'api.views.objectdiff',
        return_value=FakeDiffResult()
    )
    def test_node_found(self, m_diff, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, self.body)
        self.assertEquals(resp.status_code, status.HTTP_200_OK)
        data = resp.json()

        self.assertTrue(isinstance(data['data'], dict))
        self.assertEquals(data['nodecount'], 5)
        self.assertEquals(data['node'], 'node')


class TestObjectDiffViewSetNodes(BaseApiTestCase):

    baseurl = '/api/objectdiffs/nodes/'

    def setUp(self):
        super(TestObjectDiffViewSetNodes, self).setUp()
        self.body = {
            'model': 'Environment',
            'identity': 'someid',
            'left_time': 1,
            'right_time': 2,
            'offset': 0,
            'limit': 10
        }

    def test_without_auth(self):
        resp = self.client.post(self.baseurl, {})
        self.assertEquals(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_req(self):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, {})
        self.assertEquals(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('api.query.Query.fetch', return_value=[])
    def test_left_not_found(self, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, self.body)
        self.assertEquals(resp.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('api.query.Query.fetch', side_effect=[[], [1]])
    def test_right_not_found(self, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, self.body)
        self.assertEquals(resp.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('api.query.Query.fetch', side_effect=[[1], [1]])
    @mock.patch('api.views.objectdiff', side_effect=JobRunningError())
    def test_job_running(self, m_diff, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, self.body)
        self.assertEquals(resp.status_code, status.HTTP_202_ACCEPTED)

    @mock.patch('api.query.Query.fetch', side_effect=[[1], [1]])
    @mock.patch('api.views.objectdiff', side_effect=JobError())
    def test_job_error(self, m_diff, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, self.body)
        self.assertEquals(
            resp.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    @mock.patch('api.query.Query.fetch', side_effect=[[1], [1]])
    @mock.patch('api.views.objectdiff', return_value=FakeDiffResult())
    def test_nodes(self, m_diff, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, self.body)
        self.assertEquals(resp.status_code, status.HTTP_200_OK)

        data = resp.json()
        self.assertTrue(isinstance(data['data'], dict))
        self.assertEquals(data['nodecount'], 5)
        self.assertListEqual(data['nodes'], [1, 2, 3])


class TestObjectDiffViewSetStructure(BaseApiTestCase):

    baseurl = '/api/objectdiffs/structure/'

    def setUp(self):
        super(TestObjectDiffViewSetStructure, self).setUp()
        self.body = {
            'model': 'Environment',
            'identity': 'someid',
            'left_time': 1,
            'right_time': 2
        }

    def test_without_auth(self):
        resp = self.client.post(self.baseurl, {})
        self.assertEquals(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_req(self):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, {})
        self.assertEquals(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('api.query.Query.fetch', return_value=[])
    def test_left_not_found(self, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, self.body)
        self.assertEquals(resp.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('api.query.Query.fetch', side_effect=[[], [1]])
    def test_right_not_found(self, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, self.body)
        self.assertEquals(resp.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('api.query.Query.fetch', side_effect=[[1], [1]])
    @mock.patch('api.views.objectdiff', side_effect=JobRunningError())
    def test_job_running(self, m_diff, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, self.body)
        self.assertEquals(resp.status_code, status.HTTP_202_ACCEPTED)

    @mock.patch('api.query.Query.fetch', side_effect=[[1], [1]])
    @mock.patch('api.views.objectdiff', side_effect=JobError())
    def test_job_error(self, m_diff, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, self.body)
        self.assertEquals(
            resp.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    @mock.patch('api.query.Query.fetch', side_effect=[[1], [1]])
    @mock.patch('api.views.objectdiff', return_value=FakeDiffResult())
    def test_frame(self, m_diff, m_fetch):
        self.client.login(**self.credentials)
        resp = self.client.post(self.baseurl, self.body)
        self.assertEquals(resp.status_code, status.HTTP_200_OK)

        data = resp.json()
        self.assertTrue(isinstance(data['data'], dict))
        self.assertEquals(data['nodecount'], 5)
        self.assertEquals(data['nodemap'], 'nodemap')
        self.assertEquals(data['frame'], 'frame')
