import logging
import requests

from django.conf import settings
from .user import RaxAuthUser

logger = logging.getLogger(__name__)


class RaxAuthBackend:
    """Auth backend for authenticating internally with rackspace."""
    def __init__(self):
        """Init the backend with settings."""
        self.auth_url = settings.RAXAUTH_AUTH_URL

    def authenticate(self, request, sso=None, rsa=None):
        """Authenticate by sso and rsa token.

        :param request: Http request
        :type request:
        :param sso: SSO username.
        :type sso: str
        :param rsa: RSA token
        :type rsa: str
        :returns: User on success, None otherwise.
        :rtype:  RaxAuthUser|None
        """
        if sso and rsa:
            req = {
                "auth": {
                    "RAX-AUTH:domain": {"name": "Rackspace"},
                    "RAX-AUTH:rsaCredentials": {
                        "username": sso,
                        "tokenKey": rsa
                    }
                }
            }
            r = requests.post('{}/tokens'.format(self.auth_url), json=req)
            if r.status_code != 200:
                return None
            token = r.json()
            return RaxAuthUser(token)
        return None

    def get_user(self, user_id):
        """Get a RaxAuthUser from session.

        REQUIRES the rax auth middleware to patch the backend with the request.

        :param user_id: Id of the user
        :type user_id: str
        :returns: RaxAuthUser on success, None otherwise
        :rtype: RaxAuthUser|None
        """
        if hasattr(self, 'request') and \
                user_id == self.request.session['user_id']:
            token = self.request.session['token']
            user = RaxAuthUser(token)
            return user
        return None
