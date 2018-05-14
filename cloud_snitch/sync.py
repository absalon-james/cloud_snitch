"""Quick module for running snitchers.

Expect this to change into something configured by yaml.
Snitchers will also probably become python entry points.
"""
import argparse
import logging
import time

from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import as_completed

from itertools import groupby

from cloud_snitch.snitchers.apt import AptSnitcher
from cloud_snitch.snitchers.configfile import ConfigfileSnitcher
from cloud_snitch.snitchers.environment import EnvironmentSnitcher
from cloud_snitch.snitchers.git import GitSnitcher
from cloud_snitch.snitchers.host import HostSnitcher
from cloud_snitch.snitchers.pip import PipSnitcher
from cloud_snitch.snitchers.uservars import UservarsSnitcher

from cloud_snitch import runs
from cloud_snitch import utils
from cloud_snitch.driver import DriverContext
from cloud_snitch.exc import RunInvalidStatusError
from cloud_snitch.exc import RunAlreadySyncedError
from cloud_snitch.exc import RunContainsOldDataError
from cloud_snitch.models import EnvironmentEntity
from cloud_snitch.lock import lock_environment

logger = logging.getLogger(__name__)


parser = argparse.ArgumentParser(
    description="Ingest collected snitch data to neo4j."
)
parser.add_argument(
    '--concurrency',
    type=int,
    default=1,
    help="How many concurrent processes to use."
)


def check_run_time(driver, run):
    """Prevent a run from updating an environment.

    Protects an environment with newer data from a run with older data.

    :param driver: Neo4J database driver instance
    :type driver: neo4j.v1.GraphDatabase.driver
    :param run: Date run instance
    :type run: cloud_snitch.runs.Run
    """
    # Check to see if run data is new
    with driver.session() as session:
        e_id = '-'.join([
            run.environment_account_number,
            run.environment_name
        ])
        e = EnvironmentEntity.find(session, e_id)

        # If the environment exists, check its last update
        if e is not None:
            last_update = utils.utcdatetime(e.last_update(session) or 0)
            logger.debug(
                "Comparing {} to {}".format(run.completed, last_update)
            )
            if run.completed <= last_update:
                raise RunContainsOldDataError(run, last_update)


def consume(driver, run):
    snitchers = [
        EnvironmentSnitcher(driver, run),
        GitSnitcher(driver, run),
        HostSnitcher(driver, run),
        ConfigfileSnitcher(driver, run),
        PipSnitcher(driver, run),
        AptSnitcher(driver, run),
        UservarsSnitcher(driver, run)
    ]

    for snitcher in snitchers:
        snitcher.snitch()


def sync(paths):
    with DriverContext() as driver:
        for path in paths:
            run = runs.Run(path)
            with lock_environment(driver, run):
                try:
                    check_run_time(driver, run)
                    run.start()
                    logger.info("Starting collection on {}".format(run.path))
                    consume(driver, run)
                    logger.info("Run completion time: {}".format(
                        utils.milliseconds(run.completed)
                    ))
                    run.finish()
                except RunAlreadySyncedError as e:
                    logger.info(e)
                except RunInvalidStatusError as e:
                    logger.info(e)
                except RunContainsOldDataError as e:
                    logger.info(e)
                except Exception:
                    logger.exception('Unable to complete run.')
                    run.error()


def sort_key(item):
    """Returns a string to sort by for a run.

    Meant to be the key function in sorted()

    :param item: Run instance
    :type item: cloud_snitch.runs.Run
    :returns: String to sort by
    :rtype: str
    """
    return '{}~{}~{}'.format(
        item.environment_account_number,
        item.environment_name,
        item.completed.isoformat()
    )


def groupby_key(item):
    """Returns a string to group runs by.

    Meant to be the key function in itertools.groupby

    :param item: Run instance
    :type item: cloud_snitch.runs.Run
    :returns: String to group runs by
    :rtype: str
    """
    return '{}~{}'.format(
        item.environment_account_number,
        item.environment_name
    )


def main():
    start = time.time()
    args = parser.parse_args()
    foundruns = runs.find_runs()
    foundruns = sorted(foundruns, key=sort_key)
    with ProcessPoolExecutor(max_workers=args.concurrency) as executor:
        future_to_sync = set()
        for _, group in groupby(foundruns, groupby_key):
            paths = [r.path for r in group]
            future_to_sync.add(executor.submit(sync, paths))

        for future in as_completed(future_to_sync):
            try:
                future.result()
            except Exception:
                logger.exception(
                    'An exception occurred while processing group.'
                )
    logger.info("Finished in {} seconds".format(time.time() - start))


if __name__ == '__main__':
    main()
