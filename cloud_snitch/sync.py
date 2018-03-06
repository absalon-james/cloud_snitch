"""Quick module for running snitchers.

Expect this to change into something configured by yaml.
Snitchers will also probably become python entry points.
"""
import logging
import runs

from snitchers.apt import AptSnitcher
from snitchers.configfile import ConfigfileSnitcher
from snitchers.environment import EnvironmentSnitcher
from snitchers.git import GitSnitcher
from snitchers.host import HostSnitcher
from snitchers.pip import PipSnitcher
from snitchers.uservars import UservarsSnitcher


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
    foundruns = runs.find_runs()
    for run in foundruns:
        runs.set_current(run)
        run.update()
        logger.debug('Found run {}'.format(runs.get_current().completed))
    # main()
