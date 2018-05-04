"""Quick module for running snitchers.

Expect this to change into something configured by yaml.
Snitchers will also probably become python entry points.
"""
import logging

from cloud_snitch.snitchers.apt import AptSnitcher
from cloud_snitch.snitchers.configfile import ConfigfileSnitcher
from cloud_snitch.snitchers.environment import EnvironmentSnitcher
from cloud_snitch.snitchers.git import GitSnitcher
from cloud_snitch.snitchers.host import HostSnitcher
from cloud_snitch.snitchers.pip import PipSnitcher
from cloud_snitch.snitchers.uservars import UservarsSnitcher

from cloud_snitch import runs
from cloud_snitch import settings
from cloud_snitch import utils
from cloud_snitch.driver import driver
from cloud_snitch.exc import RunInvalidStatusError
from cloud_snitch.exc import RunAlreadySyncedError
from cloud_snitch.exc import RunContainsOldDataError
from cloud_snitch.models import EnvironmentEntity
from cloud_snitch.lock import lock_environment

logger = logging.getLogger(__name__)


def check_run_time(run):
    """Prevent a run from updating an environment.

    Protects an environment with newer data from a run with older data.

    :param run: Date run instance
    :type run: cloud_snitch.runs.Run
    """
    # Check to see if run data is new
    with driver.session() as session:
        e_id = '-'.join([
            settings.ENVIRONMENT['account_number'],
            settings.ENVIRONMENT['name']
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


def main():
    snitchers = [
        EnvironmentSnitcher(),
        GitSnitcher(),
        HostSnitcher(),
        ConfigfileSnitcher(),
        PipSnitcher(),
        AptSnitcher(),
        UservarsSnitcher()
    ]

    for snitcher in snitchers:
        snitcher.snitch()


def sync():
    try:
        foundruns = runs.find_runs()
        for run in foundruns:
            runs.set_current(run)
            with lock_environment() as lock:
                try:
                    check_run_time(run)
                    run.start()
                    logger.info("Starting collection on {}".format(run.path))
                    main()
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
            runs.unset_current()
    finally:
        driver.close()


if __name__ == '__main__':
    sync()
