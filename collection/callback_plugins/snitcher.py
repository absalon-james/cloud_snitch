from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import datetime
import hashlib
import json
import os
import yaml

from ansible.plugins.callback import CallbackBase

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
    type: ?
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

    def md5_from_string(self, s):
        """Get md5 hex digest from string.

        :param s: Source string
        :type s: str
        :returns: md5 hex digest
        :rtype: str
        """
        m = hashlib.md5()
        m.update(s)
        return m.hexdigest()

    def md5_from_file(self, name):
        """Get md5 from file from previous run.

        :param name: Name of the file containing the md5 hexdigest
        :type name: str
        :returns: Md5 hexdigest stored in file
        :rtype: str|None
        """
        try:
            with open(name, 'r') as f:
                m = f.read()
        except IOError:
            return None
        return m

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
        # Make the filenames
        outfile_name = '{}_{}.json'.format(doctype, host)
        outmd5_name = '{}_{}.md5'.format(doctype, host)
        outfile_name = os.path.join(self.basedir, outfile_name)
        outmd5_name = os.path.join(self.basedir, outmd5_name)

        # Get existing md5 sum
        existing_checksum = self.md5_from_file(outmd5_name)
        json_result = json.dumps(result.get('payload', {}))
        json_checksum = self.md5_from_string(json_result)

        # Write only if change detected
        if existing_checksum != json_checksum:
            with open(outfile_name, 'w') as f:
                f.write(json_result)
            with open(outmd5_name, 'w') as f:
                f.write(json_checksum)


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
        outmd5_name = '{}.md5'.format(self.filename_prefix)
        outfile_name = os.path.join(self.basedir, outfile_name)
        outmd5_name = os.path.join(self.basedir, outmd5_name)

        # Get existing checksum
        existing_checksum = self.md5_from_file(outmd5_name)
        json_result = json.dumps(result.get('payload', {}))
        json_checksum = self.md5_from_string(json_result)

        # Write only if change detected
        if existing_checksum != json_checksum:
            with open(outfile_name, 'w') as f:
                f.write(json_result)
            with open(outmd5_name, 'w') as f:
                f.write(json_checksum)


class GitFileHandler(SingleFileHandler):
    filename_prefix = 'gitrepos'


class UservarsHandler(SingleFileHandler):
    filename_prefix = 'uservars'


class ConfigFileHandler(FileHandler):

    def __init__(self, writedir):
        """Init the config file handler

        :param writedir: Directory to write to
        :type writedir: str
        """
        super(ConfigFileHandler, self).__init__(writedir)

    def _handle_file(self, host, filename, contents):
        """Handles a single config file.

        :param host: Name of the host
        :type host: str
        :param filename: Name of the config file
        :type filename: str
        :param contents: Config file contents
        :type contents: str
        """
        if not contents:
            contents = ''
        config_part = 'config_{}'.format(host)
        if filename.startswith(os.path.sep):
            _, filename = filename.split(os.path.sep, 1)
        outfile_name = os.path.join(self.basedir, config_part, filename)
        outmd5_name = "{}.md5".format(outfile_name)

        dirname = os.path.dirname(outfile_name)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        existing_md5 = self.md5_from_file(outmd5_name)
        current_md5 = self.md5_from_string(contents)

        if existing_md5 != current_md5:
            with open(outfile_name, 'w') as f:
                f.write(contents)
            with open(outmd5_name, 'w') as f:
                f.write(current_md5)

    def handle(self, doctype, host, result):
        """Handles the file_dict doctype

        Iterates over collected config files.

        :param doctype: Unused
        :type doctype: str
        :param host: Name of the host
        :type host: str
        :param result: Ansible task result
        :type result: dict
        """
        for filename, contents in result.get('payload', {}).iteritems():
            self._handle_file(host, filename, contents)


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
    'file_dict': ConfigFileHandler
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
            'started': now.isoformat()
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