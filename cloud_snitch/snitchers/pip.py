import json
import logging

from base import BaseSnitcher
from cloud_snitch.models import HostEntity
from cloud_snitch.models import PythonPackageEntity
from cloud_snitch.models import VirtualenvEntity

logger = logging.getLogger(__name__)


class PipSnitcher(BaseSnitcher):
    """Models path host -> virtualenv -> python package path in graph."""

    file_pattern = '^pip_list_(?P<hostname>.*).json$'

    def _update_python_package(self, session, virtualenv, pkg):
        """Updates python package in graph.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param virtualenv: Parent Virtualenv object
        :type virtualenv: VirtualenvEntity
        :param pkg: Python package dict. should contain name and version.
        :type pkg: dict
        :returns: PythonPackage object
        :rtype: PythonPackageEntity
        """
        pythonpkg = PythonPackageEntity(
            name=pkg.get('name'),
            version=pkg.get('version')
        )
        pythonpkg.update(session)
        return pythonpkg

    def _update_virtualenv(self, session, host, path, pkglist):
        """Update virtualenv and  update child pythonpackages

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param host: Parent host object
        :type host: HostEntity
        :param path: Path of virtualenv
        :type path: str
        :param pkglist: List of python package dicts
        :type pkglist: list
        :returns: Virtualenv object
        :rtype: VirtualenvEntity
        """
        virtualenv = VirtualenvEntity(host=host.hostname, path=path)
        pkgs = []
        virtualenv.update(session)
        for pkgdict in pkglist:
            pkgs.append(self._update_python_package(
                session,
                virtualenv,
                pkgdict)
            )
        virtualenv.pythonpackages.update(session, pkgs)
        return virtualenv

    def _snitch(self, session):
        """Orchestrates the creation of the environment.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        """
        for hostname, filename in self._find_host_tuples(self.file_pattern):
            virtualenvs = []
            host = HostEntity.find(session, hostname)
            if host is None:
                logger.warning(
                    'Unable to locate host entity {}'.format(hostname)
                )
                continue

            with open(filename, 'r') as f:
                pipdict = json.loads(f.read())
            for path, pkglist in pipdict.items():
                virtualenv = self._update_virtualenv(
                    session,
                    host,
                    path,
                    pkglist
                )
                virtualenvs.append(virtualenv)
            host.virtualenvs.update(session, virtualenvs)
