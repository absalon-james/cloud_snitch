import datetime
import mock

from django.test import SimpleTestCase

from raxauth.user import RaxAuthUser as User

hour = datetime.timedelta(hours=1)
NOW = datetime.datetime.now().replace(year=2050, microsecond=0)
HOUR_BEFORE = NOW - hour
HOUR_AFTER = NOW + hour


class TestRaxAuthUser(SimpleTestCase):

    def fake_good_user(self):
        return User({
            'access': {
                'token': {
                    'expires': NOW.isoformat(),
                    'id': 'test_token_id'
                },
                'user': {
                    'id': 'test_user_id',
                    'name': 'test_user_name',
                    'roles': [
                        {'name': 'role1'},
                        {'name': 'role2'},
                        {'name': 'role3'}
                    ]
                }
            }
        })

    def fake_empty_user(self):
        return User({})

    def test_expires(self):
        """Test expires property"""
        user = self.fake_good_user()
        self.assertEquals(user.expires, NOW)
        user = self.fake_empty_user()
        self.assertTrue(user.expires is None)

    def test_token_id(self):
        """Test token_id property."""
        user = self.fake_good_user()
        self.assertEquals(user.token_id, 'test_token_id')
        user = self.fake_empty_user()
        self.assertTrue(user.token_id is None)

    @mock.patch('raxauth.user.datetime')
    def test_token_life(self, m_dt):
        """Test token_life property and is_token_valid function"""
        m_dt.datetime = mock.Mock()
        m_dt.datetime.utcnow = mock.Mock(return_value=HOUR_BEFORE)

        # Test token with hour remaining
        user = self.fake_good_user()
        self.assertEquals(user.token_life, 3600)
        self.assertTrue(user.is_token_valid())

        # Test token an hour expired
        m_dt.datetime.utcnow = mock.Mock(return_value=HOUR_AFTER)
        self.assertEquals(user.token_life, 0)
        self.assertFalse(user.is_token_valid())

        # Test token without expiration time.
        user = self.fake_empty_user()
        self.assertEquals(user.token_life, 0)
        self.assertFalse(user.is_token_valid())

    def test_id(self):
        """Test id property."""
        user = self.fake_good_user()
        self.assertEquals(user.id, 'test_user_id')
        user = self.fake_empty_user()
        self.assertTrue(user.id is None)

    def test_name(self):
        """Test name property."""
        user = self.fake_good_user()
        self.assertEquals(user.name, 'test_user_name')
        user = self.fake_empty_user()
        self.assertTrue(user.name is None)

    def test_username(self):
        """Test username property and get_username method."""
        user = self.fake_good_user()
        self.assertEquals(user.username, 'test_user_name')
        self.assertEquals(user.get_username(), 'test_user_name')
        user = self.fake_empty_user()
        self.assertTrue(user.username is None)
        self.assertTrue(user.get_username() is None)

    def test_roles(self):
        """Test roles property."""
        user = self.fake_good_user()
        expected = ['role1', 'role2', 'role3']
        for r in expected:
            self.assertTrue(r in user.roles)
        self.assertEquals(len(user.roles), 3)

        user = self.fake_empty_user()
        self.assertEquals(len(user.roles), 0)

    def test_has_role(self):
        """Test has_role function."""
        user = self.fake_good_user()
        expected = ['role1', 'role2', 'role3']
        for r in expected:
            self.assertTrue(user.has_role(r))
        self.assertFalse(user.has_role('not_a_role'))

    @mock.patch('raxauth.user.datetime')
    def test_is_authenticated_and_is_anonymous(self, m_dt):
        """Test is_authenticated property."""
        m_dt.datetime = mock.Mock()
        m_dt.datetime.utcnow = mock.Mock(return_value=HOUR_BEFORE)

        user = self.fake_good_user()
        self.assertTrue(user.is_authenticated)
        self.assertFalse(user.is_anonymous)

        user.token = None
        self.assertFalse(user.is_authenticated)
        self.assertTrue(user.is_anonymous)

        user = self.fake_good_user()
        m_dt.datetime.utcnow = mock.Mock(return_value=HOUR_AFTER)
        self.assertFalse(user.is_authenticated)
        self.assertTrue(user.is_anonymous)

        user = self.fake_empty_user()
        self.assertFalse(user.is_authenticated)
        self.assertTrue(user.is_anonymous)
