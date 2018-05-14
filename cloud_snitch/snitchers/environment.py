import logging

from .base import BaseSnitcher
from cloud_snitch.models import EnvironmentEntity

logger = logging.getLogger(__name__)


class EnvironmentSnitcher(BaseSnitcher):
    """Models path to update graph database for an environment."""

    def _update_environment(self, session):
        """Create the environment from settings.

        Creates the environment in graph.

        :param session: Neo4j driver session.
        :type session: neo4j.v1.session.BoltSession
        :returns: Environment object
        :rtype: HostEntity
        """
        env = EnvironmentEntity(
            account_number=self.run.environment_account_number,
            name=self.run.environment_name
        )
        env.update(session, self.time_in_ms)
        return env

    def _snitch(self, session):
        """Orchestrates the creation of the environment.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        """
        self._update_environment(session)
