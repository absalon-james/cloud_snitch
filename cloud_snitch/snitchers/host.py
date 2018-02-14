import json
import logging
import os
import re

from base import BaseSnitcher
from cloud_snitch import settings
from cloud_snitch.models import EnvironmentEntity
from cloud_snitch.models import HostEntity
from cloud_snitch.models import VersionedEdgeSet

logger = logging.getLogger(__name__)


class HostSnitcher(BaseSnitcher):
    """Models path to update graph entities for an environment."""

    file_pattern = '^hostvars_(?P<hostname>.*).json$'

    def _host_from_tuple(self, host_tuple):
        """Load hostdata from json file and create HostEntity instance.

        :param host_tuple: (hostname, filename)
        :type host_tuple: tuple
        :returns: Host object
        :rtype: HostEntity
        """
        hostname, filename = host_tuple
        with open(filename, 'r') as f:
            hostjson = json.loads(f.read())

        # @TODO - Pull in host vars/facts/things
        return HostEntity(hostname=hostname)

    def _snitch(self, session):
        """Orchestrates the updating of the hosts.

        Will first create/update any host entities.
        Will then version edges from environment to each host.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        """
        hosts = []

        # Update each host entity
        for host_tuple in self._find_host_tuples(self.file_pattern):
            host = self._host_from_tuple(host_tuple)
            with session.begin_transaction() as tx:
                logger.debug("Updating host {}".format(host.hostname))
                host.update(tx)
            hosts.append(host)

        env = EnvironmentEntity(
            account_number=settings.ENVIRONMENT['account_number'],
            name=settings.ENVIRONMENT['name']
        )

        # Update edges from environment to each host.
        edges = VersionedEdgeSet('HAS_HOST', env, HostEntity)
        with session.begin_transaction() as tx:
            edges.update(tx, hosts)
