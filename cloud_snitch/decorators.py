import logging
import random
import time

from cloud_snitch.exc import MaxRetriesExceededError
from cloud_snitch import settings
from neo4j.exceptions import TransientError


logger = logging.getLogger(__name__)


def transient_retry(func):
    """Decorator to retry a function call on a neo4j TransientError.

    :param func: Callable to retry in the event of a TransientError
    :type func: callable
    :returns: Decorated func
    :rtype: callable
    """
    def decorated(*args, **kwargs):
        retries = 0
        while retries <= settings.MAX_RETRIES:
            try:
                func(*args, **kwargs)
                break
            except TransientError:
                retries += 1
                if retries > settings.MAX_RETRIES:
                    raise MaxRetriesExceededError()
                # Compute sleep time in ms before converting to seconds.
                sleeptime = random.randint(100, 500)
                sleeptime += (2 ** retries) * 100
                sleeptime = float(sleeptime) / 1000
                logger.info(
                    "Transient error detected. Sleeping {} seconds."
                    .format(sleeptime)
                )
                time.sleep(sleeptime)
    return decorated
