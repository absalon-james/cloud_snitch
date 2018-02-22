from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import glob
import os
import yaml
from ansible.plugins.action import ActionBase


USERVAR_GLOB = '/etc/openstack_deploy/user_*.yml'

EXCLUDES = set([
    '/etc/openstack_deploy/user_secrets.yml'
])

EXCLUDES_CONTAINS = [
    'secret',
    'token',
    'key',
    'password'
]


class ActionModule(ActionBase):

    def iter_uservar_files(self):
        """Iterate over all user variable files."""
        for filename in glob.glob(USERVAR_GLOB):
            if filename in EXCLUDES:
                continue
            try:
                with open(filename, 'r') as f:
                    data = yaml.load(f.read())
                    if isinstance(data, dict):
                        yield data
            except Exception:
                pass

    def filter_contains(self, key):
        """Filter keys containing exludes.

        :param key: Name of the key
        :type key: str
        :returns: True for keep, false otherwise
        :rtype: bool
        """
        for ex in EXCLUDES_CONTAINS:
            if ex in key:
                return False
        return True

    def get_vars(self, task_vars):
        """Get uservar values from taskvars using keys found in uservars."""
        result = {}
        keys = set()
        filters = [self.filter_contains]
        for data in self.iter_uservar_files():
            for key in data:
                if all([_filter(key) for _filter in filters]):
                    keys.add(key)

        for key in keys:
            result[key] = task_vars.get(key)

        return result

    def run(self, tmp=None, task_vars=None):
        """Run the action module."""
        result = super(ActionModule, self).run(tmp, task_vars)
        result.update(changed=False, payload=None, doctype='uservars')

        # Only save data if cloud snitch is enabled
        if not os.environ.get('CLOUD_SNITCH_ENABLED'):
            return result

        if task_vars is None:
            task_vars = {}
        result['payload'] = self.get_vars(task_vars)
        return result
