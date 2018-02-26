"""Quick module for running snitchers.

Expect this to change into something configured by yaml.
Snitchers will also probably become python entry points.
"""
import logging

from cloud_snitch import settings
from neo4j.v1 import GraphDatabase
from snitchers.apt import AptSnitcher
from snitchers.configfile import ConfigfileSnitcher
from snitchers.environment import EnvironmentSnitcher
from snitchers.git import GitSnitcher
from snitchers.host import HostSnitcher
from snitchers.pip import PipSnitcher
from snitchers.uservars import UservarsSnitcher

logger = logging.getLogger(__name__)


def main():
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    )

    snitchers = [
        EnvironmentSnitcher(),
        GitSnitcher(),
        HostSnitcher(),
        ConfigfileSnitcher(),
        PipSnitcher(),
        AptSnitcher(),
        UservarsSnitcher()
    ]

    with driver.session() as session:
        for snitcher in snitchers:
            snitcher.snitch(session)
    driver.close()
