import datetime
import json
import logging
import os

from cloud_snitch import settings
from cloud_snitch import utils
from cloud_snitch.exc import RunAlreadySyncedError
from cloud_snitch.exc import RunInvalidError
from cloud_snitch.exc import RunInvalidStatusError

logger = logging.getLogger(__name__)


_CURRENT_RUN = None


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
            raise RunInvalidError(self.path)
        except ValueError:
            raise RunInvalidError(self.path)

    @property
    def completed(self):
        """Get completed datetime

        :returns: The completed datetime str
        :rtype: str|None
        """
        if self._completed is None:
            try:
                raw = self.run_data.get('completed')
                self._completed = utils.strtodatetime(raw)
            except Exception:
                self._completed = None
        return self._completed

    @property
    def synced(self):
        """Get synced datetime

        :returns: The synced datetime
        :rtype: datetime
        """
        synced = self.run_data.get('synced')
        if synced is not None:
            try:
                synced = utils.strtodatetime(synced)
            except Exception:
                synced = None
        return synced

    @property
    def status(self):
        """Get status of the run.

        Status should be 'finished' before it can be synced.

        :returns: Status of the run
        :rtype: str
        """
        return self.run_data.get('status')

    @property
    def environment_account_number(self):
        """Get account number associated with the run.

        :returns: Account number
        :rtype: str
        """
        return self.run_data.get('environment', {}).get('account_number')

    @property
    def environment_name(self):
        """Get name of the environment.

        :returns: Name of the environment.
        :rtype: str
        """
        return self.run_data.get('environment', {}).get('name')

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
        self._completed = None

    def start(self):
        """Mark run as syncing.

        Changes run status to 'syncing'
        """
        self.update()
        if self.status != 'finished':
            raise RunInvalidStatusError(self)
        if self.run_data.get('synced') is not None:
            raise RunAlreadySyncedError(self)

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

    def error(self):
        """Mark run as just finished.

        An unexpected exception occurred.
        """
        self.run_data['status'] = 'finished'
        self._save_data()


def find_runs():
    """Create a list of run objects from the configured data directory.

    :returns: List of run objects
    :rtype: list
    """
    runs = []
    for root, dirs, files in os.walk(settings.DATA_DIR):
        for d in dirs:
            run_data = os.path.join(root, d, 'run_data.json')
            if os.path.isfile(run_data):
                try:
                    runs.append(Run(os.path.dirname(run_data)))
                except RunInvalidError:
                    continue

    # Sort runs be completed timestamp
    runs = sorted(runs, key=lambda r: r.completed)
    return runs


def set_current(run):
    """Set the current run

    :param run: Run instance object
    :type run: Run
    """
    global _CURRENT_RUN
    _CURRENT_RUN = run


def get_current():
    """Get the current run

    Used for context purposes.

    :returns: Current run instance
    :rtype: Run
    """
    return _CURRENT_RUN


def unset_current():
    """Unset the current run."""
    set_current(None)
