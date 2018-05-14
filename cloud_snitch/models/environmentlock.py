import logging

from .base import VersionedEntity
from cloud_snitch import utils
from cloud_snitch.exc import EnvironmentLockedError

logger = logging.getLogger(__name__)


class EnvironmentLockEntity(VersionedEntity):
    """Model an environment lock in the graph.

    A lock on an environment exists if the locked property for an
    environmentlock node is not null.
    """

    label = 'EnvironmentLock'
    state_label = 'EnvironmentLockState'
    identity_property = 'account_number_name'
    static_properties = [
        'account_number',
        'name',
        'locked'
    ]
    concat_properties = {
        'account_number_name': [
            'account_number',
            'name'
        ]
    }

    @classmethod
    def lock(cls, session, account_number, name):
        """Locks an environment with matching account number and name.

        Lock is obtained in a single transaction.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param account_number: Environment account number
        :type account_number: str
        :param name: Environment name
        :type name: str
        :returns: The time of the lock in milliseconds. This will be
            used as the key to release the lock
        :rtype: int
        """
        identity = '-'.join([account_number, name])
        lock_time = utils.milliseconds_now()
        with session.begin_transaction() as tx:
            instance = cls.find_transaction(tx, identity)
            if instance is None:
                # No node found, create the node
                instance = cls(
                    account_number=account_number,
                    name=name,
                    locked=lock_time
                )
                instance._update(tx, lock_time)
            elif instance.locked == 0:
                instance.locked = lock_time
                instance._update(tx, lock_time)
            else:
                # Raise exception. The node exists and locked is not none
                raise EnvironmentLockedError(instance)
        return lock_time

    @classmethod
    def release(cls, session, account_number, name, key):
        """Releases the lock on an environment.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param account_number: Environment account number
        :type account_number: str
        :param name: Environment name
        :type name: str
        :param key: Time of the lock in milliseconds
        :type key: int
        :returns: True for lock released or no action, False otherwise
        :rtype: bool
        """
        identity = '-'.join([account_number, name])
        release_time = utils.milliseconds_now()
        with session.begin_transaction() as tx:
            instance = cls.find_transaction(tx, identity)

            # Check for empty result
            if instance is None:
                # No node found, no instance to unlock
                return True

            # Check for instance is locked
            elif instance.locked:
                # If the instance is locked, the key must match the lock time
                if key == instance.locked:
                    instance.locked = 0
                    instance._update(tx, release_time)
                    return True
                # If the key does not match then do not release lock
                else:
                    return False

            # Nothing to release if this far
            return True
