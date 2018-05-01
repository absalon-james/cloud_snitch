#!/usr/bin/python

import os
import re
import subprocess

PIP_LIST_PATTERN = re.compile(
    '^(?P<name>.*) \((?P<version>[^ ,]*)(, (?P<path>.*)){0,1}\)$'
)

DOCUMENTATION = '''
---
module: pip_snitch

short_description: Gathers python pip package information.

version_added: "1.9.2"

description:
    - "Identifies virtual environments on host"
    - "Executes a pip list in each virtual environment"
    - "Parses pip list output"

extends_documentation_fragment:
    - azure

author:
    - James Absalon
'''

EXAMPLES = '''
# Get pip information
- name: Get data
  pip_snitch:
'''

RETURN = '''
payload:
    description: |
       Dict keyed by virtual env. The value of each virtualenv will be a list
       of dicts containing keys for package name and version
    type: dict
doctype:
    description: Type of document. Will always be 'pip_list'
    type: str
'''

FIND_VIRTUALENVS = [
    'find',
    '/',
    '-not', '-path', '/var/lib/lxc/*',
    '-not', '-path', '*/local/bin/*',
    '-regex', '.*/bin/python'
]


def parse_pips(data):
    """Parse pip location information from output of find virtualenvs.

    :param data: stdout from find virtualenvs
    :type data: str
    :returns: List of pip locations
    :rtype: list
    """
    ending = os.path.sep + 'python'
    result = []
    for line in data.split('\n'):
        # Check for empty lines
        if not line:
            continue
        # Check for lines not ending in /python
        if not line.endswith(ending):
            continue
        # Swap /python ending for /pip
        parent_dir, _ = line.rsplit(os.path.sep, 1)
        pip = os.path.join(parent_dir, 'pip')
        result.append(pip)
    return result


def parse_list(list_output):
    """Parse pip list ouput into list of dicts.

    Expects list output to be in a format similar to:
    pkg1 (version1)
    pkg2 (version2, path)
    ...
    pkgN (versionN)

    :param list_output: Output from pip list command.
    :type list_output: str
    :returns: List of python package dicts containing name and version.
    :rtype: list
    """

    pip_list = []
    for line in list_output.split('\n'):
        match = PIP_LIST_PATTERN.search(line)
        if match is None:
            continue
        pip_list.append(dict(
            name=match.group('name'),
            version=match.group('version'),
            path=match.group('path')
        ))
    return pip_list


def pip_list(pip_path):
    """Parse output of pip list from pip at pip_path

    :param pip_path: Location of pip within virtualenv
    :type pip_path: str
    :returns: List of dicts containing pkg names and versions
    :rtype: list
    """
    output = None

    # Build an alternative pip path to try
    # Non virtual env setups will usually have pip in /usr/local/bin
    # Instead of /usr/bin
    # Remove /bin/pip at end
    local_pip_path = pip_path.rsplit(os.path.sep, 2)[0]
    # Add local/bin/pip to the end
    local_pip_path = os.path.join(local_pip_path, 'local', 'bin', 'pip')

    # Try to get legacy format first. The legacy format is the format
    # of pip version 8 and below.
    commands = [
        [pip_path, 'list', '--format', 'legacy'],
        [pip_path, 'list'],
        [local_pip_path, 'list', '--format', 'legacy'],
        [local_pip_path, 'list']
    ]

    # Try all paths stopping when one works
    for command in commands:
        try:
            output = subprocess.check_output(command)
        except OSError:
            # Path not found
            continue
        except subprocess.CalledProcessError:
            # --format lecacy not supported
            continue
        if output:
            break
    # If not successful, return empty
    else:
        return []

    # Returned parsed data
    return parse_list(output)


def pips_list(pip_paths):
    """Run pip list on each pip path

    :param pip_paths: List of pip paths
    :type pip_paths: list
    :returns: dict keyed by virtual env
    :rtype: dict
    """
    pip_dict = {}
    for pip_path in pip_paths:
        virtualenv = pip_path.rsplit(os.path.sep, 2)[0]
        pip_dict[virtualenv] = pip_list(pip_path)
    return pip_dict


def run_module():
    module_args = dict()

    result = dict(
        changed=False,
        payload={},
        doctype='pip_list'
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # Find virtual environments
    try:
        venv_out = subprocess.check_output(FIND_VIRTUALENVS)
    except subprocess.CalledProcessError as e:
        venv_out = e.output

    try:
        pips = parse_pips(venv_out)
        result['payload'] = pips_list(pips)
    except Exception:
        module.fail_json(msg="Unable to collect python pkg information.")

    module.exit_json(**result)


def main():
    run_module()


from ansible.module_utils.basic import *

main()
