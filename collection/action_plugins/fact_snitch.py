from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
from ansible.plugins.action import ActionBase


class ActionModule(ActionBase):

    def get_facts(self, task_vars):
        """Pulls hostvars from task vars for the targeted host.

        Currently saves to a file named after the host.

        :param task_vars: Provided input vars
        :type task_vars: dict
        """
        # Get current host from task_vars
        hostname = task_vars.get('inventory_hostname')

        # Dump var data
        data = task_vars['hostvars'].get(hostname)

        facts = {}
        for key, val in data.items():
            if key.startswith('ansible_'):
                facts[key] = val

        return facts

    def run(self, tmp=None, task_vars=None):
        """Run the action module."""
        result = super(ActionModule, self).run(tmp, task_vars)
        result.update(changed=False, payload=None, doctype='facts')

        # Only save data if cloud snitch is enabled
        if not os.environ.get('CLOUD_SNITCH_ENABLED'):
            return result

        if task_vars is None:
            task_vars = {}
        result['payload'] = self.get_facts(task_vars)
        return result
