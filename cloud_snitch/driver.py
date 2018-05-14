import logging

from cloud_snitch import settings
from neo4j.v1 import GraphDatabase

logger = logging.getLogger(__name__)


class DriverContext():
    """Provide a driver for a context."""

    def __init__(self):
        """Init the context."""
        self.driver = None

    def __enter__(self):
        """Get an instance of the database driver according to settings.

        :returns: Instance of driver
        :rtype: neo4j.v1.GraphDatabase.driver
        """
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(
                settings.NEO4J_USERNAME,
                settings.NEO4J_PASSWORD
            )
        )
        return self.driver

    def __exit__(self, *args):
        """Close the driver."""
        self.driver.close()
