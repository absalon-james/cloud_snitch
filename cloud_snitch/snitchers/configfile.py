import hashlib
import json
import logging
import os

from .base import BaseSnitcher
from cloud_snitch.models import ConfigfileEntity
from cloud_snitch.models import EnvironmentEntity
from cloud_snitch.models import HostEntity

logger = logging.getLogger(__name__)


class ConfigfileSnitcher(BaseSnitcher):
    """Models path host -> configfile"""

    file_pattern = '^file_dict_(?P<hostname>.*).json$'

    def _update_host(self, session, hostname, filename):
        """Update configuration files for a host.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param hostname: Name of the host
        :type hostname: str
        :param filename: Name of file
        :type filename: str
        """
        # Extract config and environment data.
        with open(filename, 'r') as f:
            configdata = json.loads(f.read())
            envdict = configdata.get('environment', {})
            env = EnvironmentEntity(
                account_number=envdict.get('account_number'),
                name=envdict.get('name')
            )
            configdata = configdata.get('data', {})

        # Find parent host object - return early if not exists.
        host = HostEntity(hostname=hostname, environment=env.identity)
        host = HostEntity.find(session, host.identity)
        if host is None:
            logger.warning('Unable to locate host {}'.format(hostname))
            return

        # Iterate over configration files in the host's directory
        configfiles = []
        for filename, contents in configdata.items():
            _, name = os.path.split(filename)
            md5 = hashlib.md5()
            md5.update(contents.encode('utf-8'))
            md5 = md5.hexdigest()

            # Update configfile node
            configfile = ConfigfileEntity(
                path=filename,
                host=host.identity,
                md5=md5,
                contents=contents,
                name=name
            )
            configfile.update(session, self.time_in_ms)
            configfiles.append(configfile)

        # Update host -> configfile relationships.
        host.configfiles.update(session, configfiles, self.time_in_ms)

    def _snitch(self, session):
        """Update the apt part of the graph..

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        """
        for hostname, filename in self._find_host_tuples(self.file_pattern):
            self._update_host(session, hostname, filename)
