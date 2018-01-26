from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import pprint
import os
from ansible.plugins.action import ActionBase


class ActionModule(ActionBase):

    def save_vars(self, task_vars):
        """Pulls hostvars from task vars for the targeted host.

        Currently saves to a file named after the host.

        :param task_vars: Provided input vars
        :type task_vars: dict
        """
        # Get current host from task_vars
        hostname = task_vars.get('inventory_hostname')

        # Determine file name
        outfile_name = '{}_vars.json'.format(hostname)
        outfile_dir = os.environ.get('CLOUD_SNITCH_DIR')
        if outfile_dir:
            outfile_name = os.path.join(outfile_dir, outfile_name)

        # Dump var data
        with open(outfile_name, 'w') as f:
            data = task_vars['hostvars'].get(hostname)
            f.write(json.dumps(data))

    def run(self, tmp=None, task_vars=None):
        """Run the action module."""
        result = super(ActionModule, self).run(tmp, task_vars)
        # Only save data if cloud snitch is enabled
        if not os.environ.get('CLOUD_SNITCH_ENABLED'):
            return result

        if task_vars is None:
            task_vars = {}
        self.save_vars(task_vars)
        return result
