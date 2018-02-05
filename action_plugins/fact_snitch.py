from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import copy
import json
import pprint
import os
from ansible.plugins.action import ActionBase


def thedump(host, data):
    dirname = os.environ.get('CLOUD_SNITCH_DIR')
    filename = '{}.dump'.format(host)
    if dirname:
        filename = os.path.join(dirname, filename)

    with open(filename, 'w') as f:
        f.write(data)

class ActionModule(ActionBase):

    def get_vars(self, task_vars):
        """Pulls hostvars from task vars for the targeted host.

        Currently saves to a file named after the host.

        :param task_vars: Provided input vars
        :type task_vars: dict
        """
        # Get current host from task_vars
        hostname = task_vars.get('inventory_hostname')

        # Dump var data
        data = pprint.pformat(task_vars)
        thedump(hostname, data)
        return None

    def run(self, tmp=None, task_vars=None):
        """Run the action module."""
        result = super(ActionModule, self).run(tmp, task_vars)
        result.update(changed=False, payload=None, doctype='facts')

        # Only save data if cloud snitch is enabled
        if not os.environ.get('CLOUD_SNITCH_ENABLED'):
            return result

        if task_vars is None:
            task_vars = {}
        result['payload'] = self.get_vars(task_vars)
        return result
