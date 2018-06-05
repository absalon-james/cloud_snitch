from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject

from . import utils


def get_user(request):
    """Replacement get_user function for middleware.

    :param request: Http Request
    :type request:
    :returns: Cached user
    :rtype: RaxAuthUser
    """
    if not hasattr(request, '_cached_user'):
        request._cached_user = utils.get_user(request)
    return request._cached_user


class AuthenticationMiddleware(MiddlewareMixin):
    """Middle ware to attach user to request.

    This is a direct replacement for default django auth middleware.
    """
    def process_request(self, request):
        assert hasattr(request, 'session'), (
            "The Django authentication middleware requires session middleware "
            "to be installed. Edit your MIDDLEWARE%s setting to insert "
            "'django.contrib.sessions.middleware.SessionMiddleware' before "
            "'django.contrib.auth.middleware.AuthenticationMiddleware'."
        ) % ("_CLASSES" if settings.MIDDLEWARE is None else "")
        request.user = SimpleLazyObject(lambda: get_user(request))
