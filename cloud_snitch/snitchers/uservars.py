import json
import logging
import os

from base import BaseSnitcher
from cloud_snitch import settings
from cloud_snitch.models import EnvironmentEntity
from cloud_snitch.models import UservarEntity
from cloud_snitch.models import VersionedEdgeSet

logger = logging.getLogger(__name__)


class UservarsSnitcher(BaseSnitcher):
    """Models the following path env -> uservar"""

    def _snitch(self, session):
        """Orchestrates the creation of the environment.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        """
        # Load saved git data
        filename = os.path.join(settings.DATA_DIR, 'uservars.json')
        try:
            with open(filename, 'r') as f:
                uservars_dict = json.loads(f.read())
        except IOError:
            logger.warning('Unable to locate uservar file.')
            return

        # Try to find the parent environment.
        with session.begin_transaction() as tx:
            env = EnvironmentEntity(
                account_number=settings.ENVIRONMENT.get('account_number'),
                name=settings.ENVIRONMENT.get('name')
            )
            identity = env.identity
            env = EnvironmentEntity.find(tx, identity)
            if env is None:
                logger.warning(
                    'Unable to locate environment {}.'.format(identity)
                )
                return

        # Iterate over each uservariable
        uservars = []
        for key, val in uservars_dict.items():

            if isinstance(val, dict) or isinstance(val, list):
                val = json.dumps(val)

            uservar = UservarEntity(
                environment=env.identity,
                name=key,
                value=val
            )
            with session.begin_transaction() as tx:
                uservar.update(tx)
                uservars.append(uservar)

        # Update edges
        edges = VersionedEdgeSet('HAS_USERVAR', env, UservarEntity)
        with session.begin_transaction() as tx:
            edges.update(tx, uservars)
