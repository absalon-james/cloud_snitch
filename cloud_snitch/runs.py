import datetime
import json
import logging
import os

from cloud_snitch import settings
from cloud_snitch.exc import InvalidCollectionError

logger = logging.getLogger(__name__)


class Run:
    """Models a running of the collection of data."""

    def _read_data(self):
        """Reads run data.

        :returns: Run data loaded from file.
        :rtype: dict
        """
        try:
            with open(os.path.join(self.path, 'run_data.json'), 'r') as f:
                return json.loads(f.read())
        except IOError:
            raise InvalidCollectionError(self.path)
        except ValueError:
            raise InvalidCollectionError(self.path)

    def _save_data(self):
        """Save run data to disk"""
        with open(os.path.join(self.path, 'run_data.json'), 'w') as f:
            f.write(json.dumps(self.run_data))

    def __init__(self, path):
        """Inits the run

        :param path: Path on disk that contains the run
        :type path: str
        :param run_data: Data about the run
        :type run_data: dict
        """
        self.path = path
        self.run_data = self._read_data()

    def is_valid(self):
        """Determine if the run is a valid sync target.

        :returns: True for yes, False otherwise
        :rtype: bool
        """
        if self.run_data.get('synced') is not None:
            logger.debug('{} is already synced.'.format(self.path))
            return False
        if self.run_data.get('status') != 'finished':
            logger.debug('{} is not finished.'.format(self.path))
            return False
        return True

    def start(self):
        """Mark run as syncing.

        Changes run status to 'syncing'
        """
        self.run_data['status'] = 'syncing'
        self._save_data()

    def update(self):
        """Reload data from disk just."""
        self.run_data = self._read_data()

    def finish(self):
        """Mark run as finished.

        Changes run status to 'finished'
        Changes synced to now
        """
        self.run_data['status'] = 'finished'
        self.run_data['synced'] = datetime.datetime.utcnow().isoformat()
        self._save_data()


def find_runs():
    """Create a list of run objects from the configured data directory.

    :returns: List of run objects
    :rtype: list
    """
    runs = []
    for thing in os.listdir(settings.DATA_DIR):
        if os.path.isdir(os.path.join(settings.DATA_DIR, thing)):
            try:
                run = Run(os.path.join(settings.DATA_DIR, thing))
                if run.is_valid():
                    runs.append(run)
            except InvalidCollectionError:
                continue
    return runs
