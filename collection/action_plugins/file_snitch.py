from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import yaml
from ansible.plugins.action import ActionBase

# Attempt to load configuration
conf_file = os.environ.get(
    'CLOUD_SNITCH_CONF_FILE',
    '/etc/cloud_snitch/cloud_snitch.yml')
with open(conf_file, 'r') as f:
    settings = yaml.load(f.read())


class ActionModule(ActionBase):

    def _build_args(self):
        return dict(file_list=settings.get('file_snitch_list', []))

    def run(self, tmp=None, task_vars=None):
        """Run the action module."""
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
