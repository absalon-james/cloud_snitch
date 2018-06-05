import mock

from django.test import SimpleTestCase
from raxauth.backend import RaxAuthBackend
from raxauth.user import RaxAuthUser


class FakeRequest:

    def __init__(self, user_id=None, token=None):
        self.session = {}
        if user_id is not None:
            self.session['user_id'] = user_id
        if token is not None:
            self.session['token'] = token


class FakeResponse:

    def __init__(self, status_code=200, json=None):
        self.status_code = status_code
        self._json = json

    def json(self):
        return self._json


class TestRaxAuthBackend(SimpleTestCase):
    def test_get_user_no_request(self):
        """Test that get_user is None when request has not been attached."""
        backend = RaxAuthBackend()
        self.assertTrue(backend.get_user('test_user_id') is None)

    def test_get_user_user_id_not_in_session(self):
        """Test mismatched user_ids."""
        backend = RaxAuthBackend()
        backend.request = FakeRequest(user_id='test_user_id')
        self.assertTrue(backend.get_user('some_other_user') is None)

    def test_get_user_valid_user(self):
        """Test that matching userids in session result in RaxAuthUser"""
        backend = RaxAuthBackend()
        backend.request = FakeRequest(user_id='test_user_id', token={})
        user = backend.get_user('test_user_id')
        self.assertTrue(isinstance(user, RaxAuthUser))

    @mock.patch('raxauth.backend.requests.post')
    def test_authenticate_without_params(self, m_post):
        """Test that missing params result in None"""
        m_post.return_value = FakeResponse()
        backend = RaxAuthBackend()
        request = FakeRequest()
        user = backend.authenticate(request)
        self.assertTrue(user is None)

        user = backend.authenticate(request, sso='test_sso')
        self.assertTrue(user is None)

        user = backend.authenticate(request, rsa='test_rsa')
        self.assertTrue(user is None)

    @mock.patch('raxauth.backend.requests.post')
    def test_authenticate(self, m_post):
        """Test valid post."""
        m_post.return_value = FakeResponse(json={})
        backend = RaxAuthBackend()
        request = FakeRequest()
        user = backend.authenticate(request, sso='test_sso', rsa='test_rsa')
        self.assertTrue(isinstance(user, RaxAuthUser))

    @mock.patch('raxauth.backend.requests.post')
    def test_authenticate_non_200(self, m_post):
        """Test valid post with non 200 response."""
        m_post.return_value = FakeResponse(status_code=401, json={})
        backend = RaxAuthBackend()
        request = FakeRequest()
        user = backend.authenticate(request, sso='test_sso', rsa='test_rsa')
        self.assertTrue(user is None)
