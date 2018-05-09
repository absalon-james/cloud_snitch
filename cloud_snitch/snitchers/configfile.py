import hashlib
import logging
import os
import re

from .base import BaseSnitcher
from cloud_snitch.models import ConfigfileEntity
from cloud_snitch.models import HostEntity

logger = logging.getLogger(__name__)


class ConfigfileSnitcher(BaseSnitcher):
    """Models path host -> configfile"""

    dir_pattern = '^config_(?P<hostname>.*)$'

    def _find_host_dir_tuples(self, pattern):
        """Iterates over data dir looking for matching directories.

        :param pattern: Pattern to search for
        :type pattern: str
        :returns: List of tuples of (hostname, dirname)
        :rtype: list
        """
        basedir = self._basedir()
        host_tuples = []
        exp = re.compile(pattern)

        for f_or_d in os.listdir(basedir):
            r = exp.search(f_or_d)
            full = os.path.join(basedir, f_or_d)
            if r and os.path.isdir(full):
                host_tuples.append((r.group('hostname'), full))

        return host_tuples

    def _find_files(self, dirname):
        """Find all config files starting at dirname.

        :param dirname: Path of target directory
        :type dirname: str
        :yields: Filename relative to host
        :ytype: str
        """
        for dirpath, _, filenames in os.walk(dirname):
            for filename in filenames:
                fullname = os.path.join(dirpath, filename)
                _, childname = fullname.split(dirname)
                yield (os.path.join(dirpath, childname))

    def _update_host(self, session, hostname, dirname):
        """Update configuration files for a host.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param hostname: Name of the host
        :type hostname: str
        :param dirname: Name of directory
        :type dirname: str
        """
        # Find parent host object - return early if not exists.
        host = HostEntity.find(session, hostname)
        if host is None:
            logger.warning('Unable to locate host {}'.format(hostname))
            return

        # Iterate over configration files in the host's directory
        configfiles = []
        for filename in self._find_files(dirname):

            # Read content of file and compute md5
            fullpath = os.path.join(dirname, filename[1:])
            _, name = os.path.split(fullpath)
            try:
                with open(fullpath, 'r') as f:
                    contents = f.read()

                md5 = hashlib.md5()
                md5.update(contents.encode('utf-8'))
                md5 = md5.hexdigest()

            except IOError:
                logger.warning(
                    'Unable to gather config file information for {}.'
                    .format(fullpath)
                )

            # Update configfile node
            configfile = ConfigfileEntity(
                path=filename,
                host=host.identity,
                md5=md5,
                contents=contents,
                name=name
            )
            configfile.update(session)
            configfiles.append(configfile)

        # Update host -> configfile relationships.
        host.configfiles.update(session, configfiles)

    def _snitch(self, session):
        """Update the apt part of the graph..

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        """
        for hostname, dirname in self._find_host_dir_tuples(self.dir_pattern):
            logger.debug("Found {}".format(hostname))
            self._update_host(session, hostname, dirname)
