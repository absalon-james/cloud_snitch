from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import yaml

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


# Attempt to load configuration
conf_file = os.environ.get(
    'CLOUD_SNITCH_CONF_FILE',
    '/etc/cloud_snitch/cloud_snitch.yml')
with open(conf_file, 'r') as f:
    settings = yaml.load(f.read())


class ActionModule(ActionBase):

    def _build_args(self):
        return dict(file_list=settings.get('file_snitch_list', []))

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
        """Run the old style action module."""
        # Only save data if cloud snitch is enabled
        if not os.environ.get('CLOUD_SNITCH_ENABLED'):
            result = dict(changed=False, payload=None, doctype='file_dict')
            return ReturnData(conn=conn, result=result)

        complex_args = self._build_args()

        # Call the file_snitch module.
        result = self.runner._execute_module(
            conn,
            tmp,
            module_name,
            module_args,
            inject=inject,
            complex_args=complex_args
        )
        result.result['changed'] = False
        result.result['doctype'] = 'file_dict'
        return result

    def run_new(self, tmp=None, task_vars=None):
        """Run the new style action module."""
        result = super(ActionModule, self).run(tmp, task_vars)
        result.update(changed=False, payload=None, doctype='file_dict')

        # Only save data if cloud snitch is enabled
        if not os.environ.get('CLOUD_SNITCH_ENABLED'):
            return result

        module_args = self._build_args()
        result.update(
            self._execute_module(
                module_name='file_snitch',
                module_args=module_args,
                task_vars=task_vars,
                tmp=tmp
            )
        )
        return result

    def run(self, *args, **kwargs):
        """Run the action module."""
        if OLD:
            return self.run_old(*args, **kwargs)
        else:
            return self.run_new(*args, **kwargs)
