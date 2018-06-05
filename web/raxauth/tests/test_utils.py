import mock

from django.test import SimpleTestCase
from django.contrib.auth import (
    SESSION_KEY,
    BACKEND_SESSION_KEY
)
from raxauth.utils import get_user
from raxauth.user import RaxAuthUser


class FakeRequest:

    def __init__(self, hide_session_key=False, hide_backend_session_key=False):
        self.session = {}
        if not hide_session_key:
            self.session[SESSION_KEY] = 'session_key'
        if not hide_backend_session_key:
            self.session[BACKEND_SESSION_KEY] = 'backend_session_key'


class FakeBackend:

    def get_user(self, user_id):
        return RaxAuthUser({})


class TestGetUser(SimpleTestCase):

    fake_backend = FakeBackend()

    def test_session_key_error(self):
        """Test for when auth.SESSION_KEY is not in session."""
        req = FakeRequest(hide_session_key=True)
        user = get_user(req)
        self.assertTrue(user.is_anonymous)

    def test_backend_session_key_error(self):
        """Test for when auth.BACKEND_SESSION_KEY is not in session."""
        req = FakeRequest(hide_backend_session_key=True)
        user = get_user(req)
        self.assertTrue(user.is_anonymous)

    @mock.patch('raxauth.utils.auth.load_backend', return_value=fake_backend)
    def test_full(self, m_load):
        req = FakeRequest()
        user = get_user(req)

        # Test that req is attached to the backend
        self.assertTrue(self.fake_backend.request is req)

        # Test that we get a non anonymous user
        self.assertTrue(isinstance(user, RaxAuthUser))
