import logging
import os
import re
import time

from cloud_snitch.driver import driver
from cloud_snitch import runs

logger = logging.getLogger(__name__)


class BaseSnitcher(object):
    """Models path to update a subgraph for an environment."""

    def _basedir(self):
        """Get the base directory of the current run.

        :returns: Base directory of current run
        :rtype: str
        """
        return os.path.join(runs.get_current()).path

    def _find_host_tuples(self, pattern):
        """Iterate over datadir looking for matching files.

        Target format is 'hostvar_<hostname>.json'

        :returns: List of tuples of (hostname, filename)
        :rtype: list
        """
        basedir = self._basedir()
        host_tuples = []
        exp = re.compile(pattern)

        for f in os.listdir(basedir):
            r = exp.search(f)
            if r:
                hostname = r.group('hostname')
                host_tuples.append(
                    (hostname, os.path.join(basedir, f))
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
        start = time.time()
        logger.info("Starting snitcher {}".format(self.__class__.__name__))
        with driver.session() as session:
            self._snitch(session)
            session.close()
        logger.info("Finished in {0:.3f}s.".format(time.time() - start))
