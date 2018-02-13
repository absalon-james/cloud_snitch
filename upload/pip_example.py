import datetime
import json
import logging
import os
import pprint
import re
import settings
import utils

from neo4j.v1 import GraphDatabase

from models import EnvironmentEntity as Environment
from models import HostEntity as Host
from models import PythonPackageEntity as PythonPackage
from models import VersionedEdgeSet as VersionedEdges
from models import VirtualenvEntity as Virtualenv

logger = logging.getLogger(__name__)
DATA_DIR = os.environ.get('CLOUD_SNITCH_DIR')


def create_environment(session):
    """Create the environment from settings."""
    env = Environment(
        account_number=settings.ENVIRONMENT['account_number'],
        name=settings.ENVIRONMENT['name']
    )
    with session.begin_transaction() as tx:
        env.update(tx)
    return env


def create_python_packages(session, virtualenv, data_list):

    python_packages = []
    for data in data_list:
        python_package = PythonPackage(
            name=data['name'],
            version=data['version']
        )
        logger.debug("Found python package {}".format(python_package.name_version))
        with session.begin_transaction() as tx:
            python_package.update(tx)
        python_packages.append(python_package)

    with session.begin_transaction() as tx:
        edges = VersionedEdges('HAS_PYTHON_PACKAGE', virtualenv, PythonPackage)
        edges.update(tx, python_packages)


def create_virtualenvs(session, host, filename):
    virtualenvs = []
    filename = os.path.join(DATA_DIR, filename)
    with open(filename, 'r') as f:
        data = json.loads(f.read())
        for path, freeze in data.items():
            virtualenv = Virtualenv(host=host.hostname, path=path)
            logger.debug("Found virtualenv: {}".format(virtualenv.path_host))
            with session.begin_transaction() as tx:
                virtualenv.update(tx)
            virtualenvs.append(virtualenv)
            create_python_packages(session, virtualenv, freeze)

        with session.begin_transaction() as tx:
            edges = VersionedEdges('HAS_VIRTUALENV', host, Virtualenv)
            edges.update(tx, virtualenvs)


def create_hosts(session, env):
    """Create hosts and environment->host relationship."""
    pippattern = '^pip_list_(?P<hostname>.*).json$'
    exp = re.compile(pippattern)

    hosts = []
    for f in os.listdir(DATA_DIR):
        r = exp.search(f)
        if r:
            hostname = r.group('hostname')
            host = Host(hostname=hostname)
            logger.debug('Found host: {}'.format(hostname))
            with session.begin_transaction() as tx:
                host.update(tx)

            create_virtualenvs(session, host, f)
            hosts.append(Host(hostname=r.group('hostname')))

    with session.begin_transaction() as tx:
        edges = VersionedEdges('HAS_HOST', env, Host)
        edges.update(tx, hosts)


if __name__ == '__main__':
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )

    with driver.session() as session:
        env = create_environment(session)
        create_hosts(session, env)
    driver.close()
