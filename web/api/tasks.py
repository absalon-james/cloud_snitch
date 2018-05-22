from __future__ import absolute_import, unicode_literals

import logging

from celery import shared_task
from celery.exceptions import TimeoutError as CeleryTimeoutError

from django.core.cache import cache

from .cache import cache_key
from .diff import Diff
from .diff import DiffResult

from .exceptions import JobError
from .exceptions import JobRunningError


logger = logging.getLogger(__name__)
STATUS_RUNNING = 1
STATUS_ERROR = 2
TIMEOUT = 60 * 60 * 24
ERROR_TIMEOUT = 60 * 5


def _diff_cache_key(model, identity, left_time, right_time):
    """Convenience method for computing cache key for a diff operation.

    :param model: Name of the model
    :type model: str
    :param identity: Id of an object
    :type identity: str
    :param left_time: Milliseconds since epoch on left side
    :type left_time: int
    :param right_time: Milliseconds since epoch on right side
    :type right_time: int
    :returns: Cache key for diff op
    :rtype: str
    """
    key = cache_key(
        (model, identity, left_time, right_time),
        {},
        prefix='diffdict'
    )
    return key


@shared_task
def _diffdict(model, identity, left_time, right_time):
    """Asynchronous task for diffing an object.

    :param model: Name of the model
    :type model: str
    :param identity: Id of an object
    :type identity: str
    :param left_time: Milliseconds since epoch on left side
    :type left_time: int
    :param right_time: Milliseconds since epoch on right side
    :type right_time: int
    :returns: Result of diff operation
    :rtype: DiffResult
    """
    # Mark the diff as running to prevent multiple requests from sechduling
    # the same job.
    key = _diff_cache_key(model, identity, left_time, right_time)

    # Compute the diff.
    try:
        d = Diff(model, identity, left_time, right_time)
        r = d.result()
        cache.set(key, r.diffdict, TIMEOUT)
        return r.diffdict
    except Exception as e:
        logger.exception('Unable to complete diff.')
        cache.set(key, STATUS_ERROR, ERROR_TIMEOUT)


def objectdiff(model, identity, left_time, right_time):
    """Gets the diff of an object from cache or raises an error.

    :param model: Name of the model
    :type model: str
    :param identity: Id of an object
    :type identity: str
    :param left_time: Milliseconds since epoch on left side
    :type left_time: int
    :param right_time: Milliseconds since epoch on right side
    :type right_time: int
    :returns: Result of cached diff operation
    :rtype: diff.DiffResult
    """
    # Try to get from cache first
    key = _diff_cache_key(model, identity, left_time, right_time)
    logger.debug("Looking up cache with key: {}".format(key))
    cached = cache.get(key)

    # If cached is none - Schedule the task
    if cached is None:
        logger.debug("CACHE MISS")
        try:
            # Set the key to prevent multiple same jobs.
            cache.set(key, STATUS_RUNNING, TIMEOUT)

            # Schedule the task
            task = _diffdict.delay(model, identity, left_time, right_time)

            # Wait an initial amount of time
            data = task.get(timeout=2)
            return DiffResult(data)
        except CeleryTimeoutError:
            logger.debug("Try looking later.")
            raise JobRunningError()

    # Raise error if job is still running.
    elif cached == STATUS_RUNNING:
        logger.debug("CACHE HIT -- STILL RUNNING")
        raise JobRunningError()

    # Raise error if job is in error state
    elif cached == STATUS_ERROR:
        logger.debug('CACHE HIT -- ERROR')
        raise JobError()

    # Return diff result
    else:
        logger.debug("CACHE HIT")
        return DiffResult(cached)
