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

    def playbook_on_start(self):
        """Reset data."""
        self._data = {}

    def playbook_on_stats(self, stats):
        """Dump collected data to a file.

        Using this to figure out when a playbook is done.
        """
        # Do not write if empty
        if not self._data:
            return
        outfile_name = datetime.datetime.utcnow().isoformat()
        outfile_dir = os.environ.get('CLOUD_SNITCH_DIR', '')
        if outfile_dir:
            outfile_name = os.path.join(outfile_dir, outfile_name)
        with open(outfile_name, 'w') as f:
            f.write(json.dumps(self._data))

    def runner_on_ok(self, host, result):
        """Runs on every task completion.

        Save data for the run so far.
        """
        doctype = result.get('doctype')
        if not doctype in TARGET_DOCTYPES:
            return
        docdict = self._data.setdefault(doctype, {})
        hostdict = docdict.setdefault(host, result)
