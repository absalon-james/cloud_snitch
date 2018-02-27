import logging

from cloud_snitch import settings
from neo4j.v1 import GraphDatabase

logger = logging.getLogger(__name__)

driver = GraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(
        settings.NEO4J_USERNAME,
        settings.NEO4J_PASSWORD
    )
)
