#!/usr/bin/python

import os
import subprocess

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = '''
---
module: pip_snitch

short_description: Gathers python pip package information.

version_added: "2.1.6"

description:
    - "Identifies virtual environments on host"
    - "Executes a pip freeze in each virtual environment"
    - "Parses pip freeze output"

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


def parse_freeze(freeze_output):
    """Parse pip freeze ouput into list of dicts.

    Expects freeze output to be in a format similar to:
    pkg1==version1
    pkg2==version2
    ...
    pkgN==versionN

    :param freeze_output: Output from pip freeze command.
    :type freeze_output: str
    :returns: List of python package dicts containing name and version.
    :rtype: list
    """
    pip_list = []
    for line in freeze_output.split('\n'):
        if not line:
            continue
        name, version = line.split('==')
        pip_list.append(dict(name=name, version=version))
    return pip_list


def pip_freeze(pip_path):
    """Parse output of pip freeze from pip at pip_path

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

    # Try all paths stopping when one works
    for path in [pip_path, local_pip_path]:
        try:
            output = subprocess.check_output([path, 'freeze'])
        except OSError:
            # Path not found
            continue
        if output:
            break
    # If not successful, return empty
    else:
        return []

    # Returned parsed data
    return parse_freeze(output)


def pips_freeze(pip_paths):
    """Run pip freeze on each pip path

    :param pip_paths: List of pip paths
    :type pip_paths: list
    :returns: dict keyed by virtual env
    :rtype: dict
    """
    pip_dict = {}
    for pip_path in pip_paths:
        virtualenv = pip_path.rsplit(os.path.sep, 2)[0]
        pip_dict[virtualenv] = pip_freeze(pip_path)
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
        result['payload'] = pips_freeze(pips)
    except Exception:
        module.fail_json(msg="Unable to collect python pkg information.")

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
