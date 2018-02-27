import logging
import os
import re

from cloud_snitch import settings
from cloud_snitch.driver import driver

logger = logging.getLogger(__name__)


class BaseSnitcher(object):
    """Models path to update a subgraph for an environment."""

    def _find_host_tuples(self, pattern):
        """Iterate over datadir looking for matching files.

        Target format is 'hostvar_<hostname>.json'

        :returns: List of tuples of (hostname, filename)
        :rtype: list
        """
        host_tuples = []
        exp = re.compile(pattern)

        for f in os.listdir(settings.DATA_DIR):
            r = exp.search(f)
            if r:
                hostname = r.group('hostname')
                host_tuples.append(
                    (hostname, os.path.join(settings.DATA_DIR, f))
                )

        return host_tuples

    def _snitch(self, session):
        """All subclasses must implement this.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        """
        raise NotImplementedError('Snitch method not implemented.')

    def snitch(self):
        """Orchestrates the creation of the environment.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        """
        with driver.session() as session:
            self._snitch(session)
