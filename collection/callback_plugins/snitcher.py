from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import datetime
import json
import os
import yaml

try:
    from ansible.plugins.callback import CallbackBase
except ImportError:
    class CallbackBase(object):
        def __init__(self, *args, **kwargs):
            pass

# Attempt to load configuration
conf_file = os.environ.get(
    'CLOUD_SNITCH_CONF_FILE',
    '/etc/cloud_snitch/cloud_snitch.yml')
with open(conf_file, 'r') as f:
    settings = yaml.load(f.read())

DOCUMENTATION = '''
    callback: snitcher
    short_description: Gathers output from cloud snitch modules
    version_added: "2.1.6"
    description:
      - This callback dumps apt_sniffer module results to a file
      - Environment Variable CLOUD_SNITCH_ENABLED
      - Environment Variable CLOUD_SNITCH_CONF_FILE
    requirements:
'''


class FileHandler:

    def __init__(self, writedir):
        """Init the file handler

        :param writedir: Directory to write to
        :type writedir: str
        """
        self.basedir = writedir
        if self.basedir is None:
            raise Exception("No data directory configured.")

        self._doc = {
            'environment': {
                'account_number': settings['environment']['account_number'],
                'name': settings['environment']['name']
            }
        }

    def _save(self):
        """Save contents of _doc to file.

        Data is encoded as json.
        """
        data = json.dumps(self._doc)
        with open(self._outfile_name, 'w') as f:
            f.write(data)

    def handle(self, doctype, host, result):
        """Writes payload as json to file.

        Stores md5 of json. Used to determine if change
        has occurred.

        Filenames will be:
            <doctype>_<host>.json, <doctype>_<host>.json


        :param doctype: Type of the document.
        :type doctype: str
        :param host: The host
        :type host: str
        :param result: The output result from ansible task
        :type result: dict
        """
        outfile_name = '{}_{}.json'.format(doctype, host)
        self._outfile_name = os.path.join(self.basedir, outfile_name)
        self._doc['host'] = host
        self._doc['data'] = result.get('payload', {})
        self._save()


class SingleFileHandler(FileHandler):

    filename_prefix = 'single'

    def handle(self, doctype, host, result):
        """Handles a a single file output from a snitch.

        Should only be called on one host. The execution will happen
        on the deployment host.

        Stored files will be:
            <filename_prefix>.json, <filename_prefix>.md5

        :param doctype: Type of document
        :type doctype: str
        :param host: Unused
        :type host: str
        :param result: Result of task|action
        :type result: dict
        """
        outfile_name = '{}.json'.format(self.filename_prefix)
        self._outfile_name = os.path.join(self.basedir, outfile_name)
        self._doc['data'] = result.get('payload', {})
        self._save()


class GitFileHandler(SingleFileHandler):
    filename_prefix = 'gitrepos'


class UservarsHandler(SingleFileHandler):
    filename_prefix = 'uservars'


TARGET_DOCTYPES = [
    'dpkg_list',
    'facts',
    'pip_list',
    'file_dict',
    'gitrepos',
    'uservars'
]

DOCTYPE_HANDLERS = {
    'dpkg_list': FileHandler,
    'facts': FileHandler,
    'pip_list': FileHandler,
    'gitrepos': GitFileHandler,
    'uservars': UservarsHandler,
    'file_dict': FileHandler
}


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_NAME = 'snitcher'

    TIME_FORMAT = '%Y-%m-%d_%H-%M-%S'

    def __init__(self, display=None):
        """Enables or disables plugin based on environment."""
        super(CallbackModule, self).__init__(display)
        self.basedir = settings.get('data_dir')
        if os.environ.get('CLOUD_SNITCH_ENABLED', False):
            self.disabled = False
            if not self.basedir:
                raise Exception("No data directory configured.")
        else:
            self.disabled = True

    def runner_on_ok(self, host, result):
        """Runs on every task completion.

        Handles data emissions from task completions.

        :param host: Host name
        :type host: str
        :param result: Result from task
        :type result: dict
        """
        doctype = result.get('doctype')
        if doctype not in TARGET_DOCTYPES:
            return
        handler = DOCTYPE_HANDLERS.get(doctype, FileHandler)
        handler(self.dirpath).handle(doctype, host, result)

    def _run_data_filename(self):
        """Compute filename of run data.

        :returns: Name of the file
        :rtype: str
        """
        return os.path.join(self.dirpath, 'run_data.json')

    def _write_run_data(self, data):
        """Writes information about the run.

        :param data: Data to save
        :type data: dict
        """
        with open(self._run_data_filename(), 'w') as f:
            f.write(json.dumps(data))

    def _read_run_data(self):
        """Read information about the run

        :returns: Loaded data
        :rtype: dict
        """
        with open(self._run_data_filename(), 'r') as f:
            return json.loads(f.read())

    def playbook_on_start(self):
        """Start new directory."""
        # Name the new directory following datetime
        now = datetime.datetime.utcnow()
        self.dirpath = os.path.join(
            self.basedir,
            now.strftime(self.TIME_FORMAT)
        )

        # Create the new directory
        if not os.path.exists(self.dirpath):
            os.makedirs(self.dirpath)

        # Saved some stats
        self._write_run_data({
            'status': 'running',
            'started': now.isoformat(),
            'environment': {
                'account_number': settings['environment']['account_number'],
                'name': settings['environment']['name']
            }
        })

    def playbook_on_stats(self, stats):
        """Used as a on_playbook_end."""
        now = datetime.datetime.utcnow()

        # Get saved data
        data = self._read_run_data()

        # Update data and then save it
        data['status'] = 'finished'
        data['completed'] = now.isoformat()
        self._write_run_data(data)
