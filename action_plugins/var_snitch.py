from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import copy
import json
import pprint
import os
from ansible.plugins.action import ActionBase

FILTER_PREFIXES = ['_']
FILTER_PATHS = [
    ['omit']
]


class ActionModule(ActionBase):

    def filter_by_paths(self, data):
        """Prunes paths from data.

        :param data: Data to filter
        :type data: dict
        :returns: Pruned date
        :rtype: dict
        """
        for path in FILTER_PATHS:
            parent = data
            for i, part in enumerate(path):
                # If parent isnt a dict, stop
                if not isinstance(parent, dict):
                    break

                # Get the child
                child = parent.get(part)

                # Stop of child doesnt exist
                if child is None:
                    break

                # If this is the end, we found the path.
                if i == len(path) - 1:
                    del parent[part]

                # Advance the parent
                parent = child
        return data

    def filter_by_prefix(self, data):
        """Filter keys prefixed with '_'.

        :param data: Data to filter_by_prefix.
        :type data: dict
        :returns: Filtered data
        :rtype: dict
        """
        s = [data]
        while len(s) > 0:
            current = s.pop()
            # Only worried about keys
            if not isinstance(current, dict):
                continue
            # Grab list of keys starting with _
            deletable = []
            for key in current:
                if any([key.startswith(p) for p in FILTER_PREFIXES]):
                    deletable.append(key)

            # Delete keys starting with _
            for key in deletable:
                del current[key]

            # Add remaining keys to check
            for key in current:
                s.append(current[key])
        return data

    def get_vars(self, task_vars):
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
        data = task_vars['hostvars'].get(hostname)
        data = copy.deepcopy(data)
        data = self.filter_by_prefix(data)
        data = self.filter_by_paths(data)
        return data

    def run(self, tmp=None, task_vars=None):
        """Run the action module."""
        result = super(ActionModule, self).run(tmp, task_vars)
        result.update(changed=False, payload=None, doctype='hostvars')

        # Only save data if cloud snitch is enabled
        if not os.environ.get('CLOUD_SNITCH_ENABLED'):
            return result

        if task_vars is None:
            task_vars = {}
        result['payload'] = self.get_vars(task_vars)
        return result
