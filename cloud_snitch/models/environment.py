import logging

from .base import VersionedEntity
from .host import HostEntity
from .gitrepo import GitRepoEntity
from .uservar import UservarEntity

logger = logging.getLogger(__name__)


class EnvironmentEntity(VersionedEntity):
    """Model environment nodes in the graph."""

    label = 'Environment'
    state_label = 'EnvironmentState'
    identity_property = 'account_number_name'
    static_properties = [
        'account_number',
        'name',
    ]
    concat_properties = {
        'account_number_name': [
            'account_number',
            'name'
        ]
    }

    children = {
        'hosts': ('HAS_HOST', HostEntity),
        'gitrepos': ('HAS_GIT_REPO', GitRepoEntity),
        'uservars': ('HAS_USERVAR', UservarEntity)
    }

    def _times_query(self):
        """Build query for finding times the environment graph was updated.

        :returns: Query string with $identity parameter
        :rtype: str
        """
        cypher = """
            MATCH p = (e:{} {{ {}:$identity }})-[*]->(n)
            WITH relationships(p) AS rels
            UNWIND rels AS r
            RETURN DISTINCT r.from AS t
            ORDER BY t DESC
        """
        cypher = cypher.format(self.label, self.identity_property)
        return cypher

    def _times_updated(self, tx):
        """Query for list of times an environment was updated.

        :param tx: neo4j transaction context.
        :type tx: neo4j.v1.api.Transaction
        :returns: List of timestamps
        :rtype: list
        """
        cypher = self._times_query()
        logger.debug("Running query to gather timestamps.")
        logger.debug(cypher)
        result = tx.run(cypher, identity=self.identity)
        return [r['t'] for r in result]

    def times_updated(self, session):
        """Query for list of times an environment was updated.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :returns: List of timestamps for when the environment was updated.
        :rtype: list
        """
        with session.begin_transaction() as tx:
            return self._times_updated(tx)

    def last_update(self, session):
        """Query for the last time the environment was updated.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :returns: None or the timestamp of the last update
        :rtype: int
        """
        with session.begin_transaction() as tx:
            cypher = self._times_query()
            cypher += ' LIMIT 1'
            result = tx.run(cypher, identity=self.identity)
            record = result.single()
            if record is None:
                return None
            return record['t']
