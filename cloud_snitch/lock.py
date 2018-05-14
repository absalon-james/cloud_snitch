import contextlib
import logging

from cloud_snitch.models import EnvironmentLockEntity


logger = logging.getLogger(__name__)


class EnvironmentLock:
    """Simple class for locking an environment."""
    def __init__(self, driver, account_number, name):
        """Init the lock

        :param driver: Instance of driver
        :type driver: neo4j.v1.GraphDatabase.driver
        :param account_number: Environment account number
        :type account_number: str
        :param name: Environment name
        :type name: str
        """
        self.driver = driver
        self.account_number = account_number
        self.name = name

        # When key is 0, the lock is open
        self.key = 0

    def lock(self):
        """Lock the environment.

        Calls the entity lock method.
        Saves the key for unlocking the environment later.
        """
        with self.driver.session() as session:
            self.key = EnvironmentLockEntity.lock(
                session,
                self.account_number,
                self.name
            )

    @property
    def locked(self):
        """Return whether or not the lock is locked.

        :returns: True for locked, False otherwise
        :rtype: bool
        """
        return self.key != 0

    def release(self):
        """Releases the lock.

        No action is taken if the lock is open
        """
        # Return early if not locked
        if self.key is None:
            return

        # Call entity release method
        with self.driver.session() as session:
            released = EnvironmentLockEntity.release(
                session,
                self.account_number,
                self.name, self.key
            )

            if released:
                self.key = 0
            else:
                logger.warning(
                    'Unable to release lock with key: {}'.format(self.key)
                )


@contextlib.contextmanager
def lock_environment(driver, run):
    """Lock an environment

    Prevents multiple sync instances from updating a single environment
    at the same time.

    :param driver: Driver instance
    :type driver: neo4j.v1.GraphDatabase.driver
    :param run: Collection run data structure.
    :type run: cloud_snitch.run.Run
    :yields: The environment lock object
    :ytype: Environment
    """
    # Start the lock object
    lock = EnvironmentLock(
        driver,
        run.environment_account_number,
        run.environment_name
    )
    try:
        # Obtain the lock
        lock.lock()
        logger.debug("Obtained lock on {}: {}".format(
            lock.account_number,
            lock.key
        ))
        yield lock
    finally:
        # Attempt to release the lock
        if lock.locked:
            lock.release()
            logger.debug("Released lock on {}: {}".format(
                lock.account_number,
                lock.name)
            )
