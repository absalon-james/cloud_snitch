import json
import logging

from base import BaseSnitcher
from cloud_snitch.models import AptPackageEntity
from cloud_snitch.models import HostEntity
from cloud_snitch.models import VersionedEdgeSet

logger = logging.getLogger(__name__)


class AptSnitcher(BaseSnitcher):
    """Models path host -> virtualenv -> python package path in graph."""

    file_pattern = '^dpkg_list_(?P<hostname>.*).json$'

    def _update_apt_package(self, session, pkgdict):
        """Updates apt package in graph.

        Will only update the apt package if status = installed

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param pkgdict: apt package dict.
            should contain name and version and status.
        :type pkg: dict
        :returns: AptPackage object or None for no action
        :rtype: AptPackageEntity|None
        """
        if pkgdict.get('status') != 'installed':
            return None

        aptpkg = AptPackageEntity(
            name=pkgdict.get('name'),
            version=pkgdict.get('version')
        )
        logger.debug(
            "Update apt package with name: {} and version: {} from {}"
            .format(aptpkg.name, aptpkg.version, pkgdict)
        )
        with session.begin_transaction() as tx:
            aptpkg.update(tx)
        return aptpkg

    def _snitch(self, session):
        """Update the apt part of the graph..

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        """
        for hostname, filename in self._find_host_tuples(self.file_pattern):
            aptpkgs = []

            # Find host in graph, continue if host not found.
            with session.begin_transaction() as tx:
                host = HostEntity.find(tx, hostname)
                if host is None:
                    logger.warning(
                        'Unable to locate host entity {}'.format(hostname)
                    )
                    continue

            # Read data from file
            with open(filename, 'r') as f:
                aptlist = json.loads(f.read())

            # Iterate over package maps
            for aptdict in aptlist:
                aptpkg = self._update_apt_package(session, aptdict)
                if aptpkg is not None:
                    aptpkgs.append(aptpkg)

            edges = VersionedEdgeSet('HAS_APT_PACKAGE', host, AptPackageEntity)
            with session.begin_transaction() as tx:
                edges.update(tx, aptpkgs)
