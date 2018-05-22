import logging

from django.core.cache import cache
from django.conf import settings

from .cache import cache_key

logger = logging.getLogger(__name__)


def _cached_result(prefix='', timeout=None, index=0):
    """Decorator called by the class and non class cached result.

    :param prefix: Prefix for cache
    :type prefix: str
    :param timeout: TTL in seconds
    :type timeout: integer
    :param index: Position of args to key from
    :type index: integer
    :returns: decorator function.
    :rtype: function
    """
    if timeout is None:
        timeout = settings.DEFAULT_CACHE_TIMEOUT

    def wrapper(func):
        def _decorated(*args, **kwargs):
            key = cache_key(args, kwargs, prefix=prefix, index=index)
            value = cache.get(key)

            if value is None:
                logger.debug("CACHE MISS")
                value = func(*args, **kwargs)
                cache.set(key, value, timeout)
            else:
                logger.debug("CACHE HIT")
            return value
        return _decorated
    return wrapper


def cls_cached_result(prefix='', timeout=None):
    """Caching decorator for class functions.

    :param prefix: Cache key prefix
    :type prefix: str
    :param timeout: TTL in seconds
    :type timeout: int
    :returns: decorator function.
    :rtype: function
    """
    return _cached_result(
        prefix=prefix,
        timeout=timeout,
        index=1
    )


def cached_result(prefix='', timeout=None):
    """Caching decorator for non class functions.

    :param prefix: Cache key prefix
    :type prefix: str
    :param timeout: TTL in seconds
    :type timeout: int
    :returns: decorator function
    :rtype: function
    """
    return _cached_result(
        prefix=prefix,
        timeout=timeout,
        index=0
    )
