from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
    callback: snitcher
    short_description: Gathers output from cloud snitch modules
    version_added: "2.1.6"
    description:
      - This callback dumps apt_sniffer module results to a file
      - Environment Variable CLOUD_SNITCH_ENABLED
      - Environment Variable CLOUD_SNITCH_DIR
    type: ?
    requirements:
'''

import datetime
import hashlib
import json
import os

from ansible.plugins.callback import CallbackBase

TARGET_DOCTYPES = [
    'dpkg_list',
    'hostvars'
]


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_NAME = 'snitcher'

    def __init__(self, display=None):
        """Enables or disables plugin based on environment."""
        super(CallbackModule, self).__init__(display)
        if os.environ.get('CLOUD_SNITCH_ENABLED', False):
            self.disabled = False
        else:
            self.disabled = True

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

    def runner_on_ok(self, host, result):
        """Runs on every task completion.

        Handles data emissions from task completions.

        :param host: Host name
        :type host: str
        :param result: Result from task
        :type result: dict
        """
        doctype = result.get('doctype')
        if not doctype in TARGET_DOCTYPES:
            return

        outfile_name = '{}_{}.json'.format(doctype, host)
        checksum_name = '{}_{}.md5'.format(doctype, host)
        outfile_dir = os.environ.get('CLOUD_SNITCH_DIR', '')
        if outfile_dir:
            outfile_name = os.path.join(outfile_dir, outfile_name)
            checksum_name = os.path.join(outfile_dir, checksum_name)

        existing_checksum = self.md5_from_file(checksum_name)

        json_result = json.dumps(result)
        json_checksum = self.md5_from_string(json_result)

        if existing_checksum != json_checksum:
            with open(outfile_name, 'w') as f:
                f.write(json_result)
            with open(checksum_name, 'w') as f:
                f.write(json_checksum)
