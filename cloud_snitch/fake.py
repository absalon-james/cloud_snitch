"""Quick module for generating fake data from real data."""
import argparse
import datetime
import glob
import json
import logging
import os
import pytz

from cloud_snitch import settings
from cloud_snitch.runs import Run
from cloud_snitch.exc import RunInvalidError

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(
    description="Create fake data sets from a real data set."
)
parser.add_argument(
    '--environments',
    type=int,
    default=10,
    help="How many environments to fake."
)
parser.add_argument(
    '--runs',
    type=int,
    default=1,
    help="How many data sets per environment."
)
parser.add_argument(
    '--output-dir',
    type=str,
    default=settings.DATA_DIR,
    help='Directory in which to place generated data.'
)
parser.add_argument(
    'run',
    type=str,
    help="Location of run to generate fakes from."
)


def increment_time(dt, delta_seconds):
    """Adds a specified number of seconds to a datetime.datetime.

    :param dt: Datetime object to increase
    :type dt: datetime.datetime
    :param delta_seconds: Number of seconds to add
    :type delta_seconds: int
    """
    return dt + datetime.timedelta(seconds=delta_seconds)


def iter_run_files(run):
    """Yields a full path for every .json file in a run.

    :param run: Run object to generate files for.
    :type run: cloud_snitch.run.Run
    :yields: Full path of a json file
    :ytype: str
    """
    for f in os.listdir(run.path):
        full = os.path.join(run.path, f)
        if os.path.isfile(full) and full.endswith('.json'):
            yield full


def copy_run(output_dir, src_run, env_number, run_number):
    """Copies an entire run and adds a suffix to the copied run's
    environment name.

    :param output_dir: Where to store copied results.
    :type output_dir: str
    :param src_run: The run to copy
    :type src_run: cloud_snitch.run.Run
    :param env_number: Suffix to add to environment name.
    :type env_number: int
    :param run_number: The number of the run
    :type run_number: int
    """
    dirname = 'fake_{}_{}'.format(
        format(env_number, '04'),
        format(run_number, '04')
    )
    envname = '{}_{}'.format(src_run.environment_name, env_number)
    dirname = os.path.join(output_dir, dirname)
    try:
        os.makedirs(dirname)
    except FileExistsError:
        files = glob.glob(os.path.join(dirname, '*'))
        for f in files:
            os.remove(f)

    for filename in iter_run_files(src_run):
        logger.info("Copying file {}".format(filename))
        with open(filename, 'r') as f:
            data = json.loads(f.read())

        if filename.endswith('run_data.json'):
            if 'synced' in data:
                del data['synced']
            completed = increment_time(
                src_run.completed,
                3600 * (run_number + 1)
            )
            completed = completed.replace(tzinfo=pytz.UTC)
            completed = completed.isoformat()[:-6]
            data['completed'] = completed

        data['environment']['name'] = envname

        _, filename = os.path.split(filename)
        filename = os.path.join(dirname, filename)
        with open(filename, 'w') as f:
            logger.info("Saving file {}".format(filename))
            f.write(json.dumps(data))


def fake(args):
    """Copies a run.

    Created a number of runs for a number of environments.

    :param args: Namespaced object from parsed arguments.
    :type args: object
    """
    try:
        run = Run(args.run)
    except RunInvalidError:
        logger.info("Run {} is invalid.".format(args.run))
        exit()

    for i in range(args.environments):
        logger.info(
            "Beginning environment {} of {}"
            .format(i + 1, args.environments)
        )
        for j in range(args.runs):
            logger.info("Beginning run {} of {}".format(j + 1, args.runs))
            copy_run(args.output_dir, run, i, j)


def main():
    """Parse args and run the fake() function."""
    args = parser.parse_args()
    fake(args)


if __name__ == '__main__':
    main()
