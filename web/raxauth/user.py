import datetime

from cloud_snitch.utils import strtodatetime
from django.contrib.auth.models import AbstractBaseUser
from django.utils.crypto import salted_hmac


class RaxAuthUser(AbstractBaseUser):
    """User class to build users from raxauth tokens."""

    USERNAME_FIELD = 'username'

    def __init__(self, token):
        """Init the user.

        All user properties will come from the token.
        """
        self.token = token

    def _token(self):
        """Get the token dict from the token.

        Auth token will look something like:
        {
            'access': {
                'token': {
                    'expires': 'somedate',
                    'id': 'token_id'
                }
            },
            'user': {
            }
        }

        :returns: Token dict
        :rtype: dict
        """
        return self.token.get('access', {}).get('token', {})

    def _user(self):
        """ Get the user dict from the token.

        Auth token will look something like:

        :returns: User dict
        :rtype: dict
        """
        return self.token.get('access', {}).get('user', {})

    @property
    def expires(self):
        """Get naive datetime of token expiration.

        :returns: Datetime of expiration of the token.
        :rtype: datetime.datetime
        """
        expires = self._token().get('expires')
        if expires is None:
            return None
        expires = strtodatetime(expires)
        expires = expires.replace(tzinfo=None)
        return expires

    @property
    def token_id(self):
        """Get the id of the token

        :returns: Token id
        :rtype: str
        """
        return self._token().get('id')

    @property
    def token_life(self):
        """Get number of seconds until token expires.

        :returns: Number of seconds remaining for token
        :rtype: int
        """
        expires = self.expires
        if expires is None:
            return 0
        now = datetime.datetime.utcnow()
        now = now.replace(tzinfo=None)
        delta = expires - now
        return max(int(delta.total_seconds()), 0)

    @property
    def id(self):
        """Get user id from token.

        :returns: Id of the raxauth user
        :rtype: str
        """
        return self._user().get('id')

    @property
    def name(self):
        """Get the name of the user from token.

        :returns: Name of the user
        :rtype: str
        """
        return self._user().get('name')

    @property
    def username(self):
        """Get the username of the user from token.

        Same as the name for now.

        :returns: Username of the user
        :rtype: str
        """
        return self.name

    def get_username(self):
        """Implementing parent class method.

        :returns: Username of the user
        :rtype: str
        """
        return self.username

    @property
    def roles(self):
        """Get roles of the user.

        Not currently user but may be used in future for authorization.

        :returns: Set of user roles
        :rtype: set
        """
        roles = set()
        for roledict in self._user().get('roles', []):
            if 'name' in roledict:
                roles.add(roledict['name'])
        return roles

    def has_role(self, role):
        """Get whether or not a user has a role.

        :param role: Role to check
        :type role: str
        :returns: True for user has role, False otherwise
        :rtype: bool
        """
        return role in self.roles

    def __unicode__(self):
        """Get unicode for username.

        :returns: Username as unicode
        :rtype: str
        """
        return self.name

    def __repr__(self):
        """Get string representation for user object.

        :returns: Representation
        :rtype: str
        """
        return "<{}: {}>".format(self.__class__.__name__, self.username)

    def is_token_valid(self):
        """Determine if token is still valid.

        Calculate remaining seconds > 0

        :returns: True for valid, False otherwise
        :rtype: bool
        """
        return self.token_life > 0

    @property
    def is_authenticated(self):
        """Determine if user is authenticated.

        User must have a valid token.

        :returns: True for authenticated, False otherwise
        :rtype: bool
        """
        return self.token and self.is_token_valid()

    @property
    def is_anonymous(self):
        """Determine if user is anonymous.

        :returns: True for anonymouse, False otherwise
        :rtype: bool
        """
        return not self.is_authenticated

    def save(self, *args, **kwargs):
        """User does not exist in database.

        Do nothing.
        """
        pass

    def delete(self, *args, **kwargs):
        """User does not exist in database.

        Do nothing.
        """
        pass

    def get_session_auth_hash(self):
        """
        Return an HMAC of the token id

        :returns: HMAC of the token id.
        :rtype: str
        """
        key_salt = "django.contrib.auth.models.AbstractBaseUser.get_session_auth_hash" # noqa E501
        return salted_hmac(key_salt, self.token_id).hexdigest()
