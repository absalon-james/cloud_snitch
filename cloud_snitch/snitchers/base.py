import logging
import os
import re
import time

from cloud_snitch import utils

logger = logging.getLogger(__name__)


class BaseSnitcher(object):
    """Models path to update a subgraph for an environment."""

    def __init__(self, driver, run):
        """Init the snitcher with a driver instance.

        :param driver: Instance of driver
        :type driver: neo4j.v1.GraphDatabase.driver
        :param run: Run information object
        :type run: cloud_snitch.runs.Run
        """
        self.driver = driver
        self.run = run
        self.time_in_ms = utils.milliseconds(run.completed)

    def _basedir(self):
        """Get the base directory of the current run.

        :returns: Base directory of current run
        :rtype: str
        """
        return os.path.join(self.run.path)

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
        logger.info("Starting snitcher {} {}".format(
            self.__class__.__name__,
            self.run.path
        ))
        with self.driver.session() as session:
            self._snitch(session)
            session.close()
        logger.info("Finished {} {} in {:.3f}s.".format(
            self.__class__.__name__,
            self.run.path,
            time.time() - start
        ))
