from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os


# Try the ansible 2.1+ style first
try:
    from ansible.plugins.action import ActionBase
    OLD = False

# Fallback to the old style
except ImportError:
    from ansible.runner.return_data import ReturnData
    OLD = True

    class ActionBase(object):
        def __init__(self, runner):
            self.runner = runner


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

    def run(self, *args, **kwargs):
        """Run the action module."""
        if OLD:
            return self.run_old(*args, **kwargs)
        else:
            return self.run_new(*args, **kwargs)

    def run_old(
        self,
        conn,
        tmp,
        module_name,
        module_args,
        inject,
        complex_args=None,
        **kwargs
    ):
        """Run version for 1.9."""
        task_vars = inject
        result = dict(changed=False, payload=None, doctype='facts')

        # Only save data if cloud snitch is enabled
        if not os.environ.get('CLOUD_SNITCH_ENABLED'):
            return ReturnData(conn=conn, result=result)

        result['payload'] = self.get_facts(task_vars)
        return ReturnData(conn=conn, result=result)

    def run_new(self, tmp=None, task_vars=None):
        """Run version for 2+."""
        if task_vars is None:
            task_vars = {}

        result = super(ActionModule, self).run(tmp, task_vars)
        result.update(changed=False, payload=None, doctype='facts')
        # Only save data if cloud snitch is enabled
        if not os.environ.get('CLOUD_SNITCH_ENABLED'):
            return result
        result['payload'] = self.get_facts(task_vars)
        return result
