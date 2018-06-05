from django.contrib import auth
from django.contrib.auth.models import AnonymousUser


def get_user(request):
    """Replacement get_user function to be consumed by raxauth middleware.

    :param request: Http request
    :type request:
    :returns: RaxAuthUser or AnonymousUser.
    :rtype: RaxAuthUser|AnonymousUser
    """
    try:
        user_id = request.session[auth.SESSION_KEY]
        backend_path = request.session[auth.BACKEND_SESSION_KEY]
        backend = auth.load_backend(backend_path)
        backend.request = request
        user = backend.get_user(user_id) or AnonymousUser()
    except KeyError:
        user = AnonymousUser()
    return user
