import logging
import settings

from neo4j.v1 import GraphDatabase

logger = logging.getLogger(__name__)

_UNIQUE_CONSTRAINTS_MAP = {
    'Envionment': 'account_number_name',
    'Host': 'hostname',
    'Pythonpackage': 'name_version',
    'Virtualenv': 'path_host',
    'PythonPackage': 'name_version'
}


if __name__ == '__main__':

    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )
    template = 'CREATE CONSTRAINT ON (n:{label}) ASSERT n.{prop} IS UNIQUE'
    with driver.session() as session:
        with session.begin_transaction() as tx:
            for label, prop in _UNIQUE_CONSTRAINTS_MAP.items():
                resp = tx.run(template.format(label=label, prop=prop))
    driver.close()
