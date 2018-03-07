"""Quick module for running snitchers.

Expect this to change into something configured by yaml.
Snitchers will also probably become python entry points.
"""
import logging

from snitchers.apt import AptSnitcher
from snitchers.configfile import ConfigfileSnitcher
from snitchers.environment import EnvironmentSnitcher
from snitchers.git import GitSnitcher
from snitchers.host import HostSnitcher
from snitchers.pip import PipSnitcher
from snitchers.uservars import UservarsSnitcher

from cloud_snitch.driver import driver
from cloud_snitch.exc import RunInvalidStatusError
from cloud_snitch.exc import RunAlreadySyncedError
from cloud_snitch import runs
from cloud_snitch import utils
from cloud_snitch.lock import lock_environment


logger = logging.getLogger(__name__)


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


if __name__ == '__main__':
    try:
        foundruns = runs.find_runs()
        for run in foundruns:
            runs.set_current(run)
            with lock_environment() as lock:
                try:
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
            runs.unset_current()
    finally:
        driver.close()
