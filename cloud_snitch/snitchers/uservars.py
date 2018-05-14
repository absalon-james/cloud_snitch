import json
import logging
import os

from .base import BaseSnitcher
from cloud_snitch.models import EnvironmentEntity
from cloud_snitch.models import UservarEntity

logger = logging.getLogger(__name__)


class UservarsSnitcher(BaseSnitcher):
    """Models the following path env -> uservar"""

    def _snitch(self, session):
        """Orchestrates the creation of the environment.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        """
        # Load saved git data
        filename = os.path.join(self._basedir(), 'uservars.json')
        try:
            with open(filename, 'r') as f:
                uservars_dict = json.loads(f.read())
        except IOError:
            logger.info('No data for uservars could be found.')
            return

        # Try to find the parent environment.
        env = EnvironmentEntity(
            account_number=self.run.environment_account_number,
            name=self.run.environment_name
        )
        identity = env.identity
        env = EnvironmentEntity.find(session, identity)
        if env is None:
            logger.warning(
                'Unable to locate environment {}.'.format(identity)
            )
            return

        # Iterate over each uservariable
        uservars = []
        for key, val in uservars_dict.get('data', {}).items():

            if isinstance(val, dict) or isinstance(val, list):
                val = json.dumps(val, sort_keys=True)

            uservar = UservarEntity(
                environment=env.identity,
                name=key,
                value=val
            )
            uservar.update(session, self.time_in_ms)
            uservars.append(uservar)

        # Update edges
        env.uservars.update(session, uservars, self.time_in_ms)
