import json
import logging
import os
import re
import settings

from neo4j.v1 import GraphDatabase

from models import EnvironmentEntity as Environment
from models import HostEntity as Host
from models import PythonPackageEntity as PythonPackage
from models import VersionedEdgeSet as VersionedEdges
from models import VirtualenvEntity as Virtualenv

logger = logging.getLogger(__name__)
DATA_DIR = os.environ.get('CLOUD_SNITCH_DIR')


def create_environment(session):
    """Create the environment from settings.

    Creates the environment in graph.

    :param session: Neo4j driver session.
    :type session: neo4j.v1.session.BoltSession
    :returns: Environment object
    :rtype: HostEntity
    """
    env = Environment(
        account_number=settings.ENVIRONMENT['account_number'],
        name=settings.ENVIRONMENT['name']
    )
    with session.begin_transaction() as tx:
        env.update(tx)
    return env


def create_python_packages(session, virtualenv, data_list):
    """Save python package information to neo4j.

    Updates pythonpackage entities in graph.
    Updates edges from virtualenv -> each pythonpackage

    :param session: neo4j driver session
    :type session: neo4j.v1.session.BoltSession
    :param virtualenv: Virtualenv object
    :type virtualenv: Virtualenv
    :param data_list: List of python package names and versions
    :type data_list: dict
    """
    python_packages = []
    for data in data_list:
        python_package = PythonPackage(
            name=data['name'],
            version=data['version']
        )
        logger.debug(
            "Found python package {}"
            .format(python_package.name_version)
        )
        with session.begin_transaction() as tx:
            python_package.update(tx)
        python_packages.append(python_package)

    with session.begin_transaction() as tx:
        edges = VersionedEdges('HAS_PYTHON_PACKAGE', virtualenv, PythonPackage)
        edges.update(tx, python_packages)


def create_virtualenvs(session, host, filename):
    """Create virtualenvs and host -> virtualenv relationship.

    Creates virtualenvs in graph.
    Creates set of edges from host to all virtualenvs.

    :param session: neo4j driver session.
    :type session: neo4j.v1.session.BoltSession
    :param host: Host object
    :type host: Host
    :param filename: Name of the file containing data.
    :type filename: str
    """
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
    """Create hosts and environment->host relationship.

    Creates hosts in graph.
    Creates set of edges from env->all hosts

    :param session: neo4j driver session
    :type session: neo4j.v1.session.BoltSession
    :param env: Environment object.
    :type env: Environment.
    """
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
        logger.debug("Type of session: {}".format(type(session)))
        env = create_environment(session)
        create_hosts(session, env)
    driver.close()
