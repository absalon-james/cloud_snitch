#!/usr/bin/python

import subprocess

#from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = '''
---
module: pkg_snitch

short_description: Gathers data on what packages are installed.

version_added: "1.9.2"

description:
    - "Parses output of dpkg-query --list."

extends_documentation_fragment:
    - azure

author:
    - James Absalon
'''

EXAMPLES = '''
# Get dpkg-query --list data
- name: Get data
  pkg_snitch:
'''

RETURN = '''
payload:
    description: List of dicts describing installed pkgs
    type: list
doctype:
    description: Type of document. Will always be 'dpkg_list'
    type: str
'''


CMD = ['dpkg-query', '--list']

DESIRED_ACTION_MAP = {
    'u': 'unknown',
    'i': 'install',
    'h': 'hold',
    'r': 'remove',
    'p': 'purge'
}

STATUS_MAP = {
    'n': 'not-installed',
    'c': 'config-files',
    'H': 'half-installed',
    'U': 'unpacked',
    'F': 'half-configured',
    'W': 'triggers-awaiting',
    't': 'triggers-pending',
    'i': 'installed'
}


def parse_out(output):
    """Parse outout of the dpkg-query --list command.

    :param output: Bytestring returned by subprocess.check_output()
    :type output: str
    :returns: List of dicts describing package states
    :rtype: list
    """
    result = []
    lines = output.split('\n')
    for i in range(5, len(lines)):
        if not lines[i]:
            continue
        status, name, version, arch, desc = lines[i].split(None, 4)
        result.append({
            'status': STATUS_MAP.get(status[1], 'unknown'),
            'desired_action': DESIRED_ACTION_MAP.get(status[0], 'unknown'),
            'name': name,
            'version': version,
            'architecture': arch,
            'description': desc
        })
    return result


def run_module():
    module_args = dict()

    result = dict(
        changed=False,
        payload=[],
        doctype='dpkg_list'
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    try:
        dpkg_out = subprocess.check_output(CMD)
        result['payload'] = parse_out(dpkg_out)
    except subprocess.CalledProcessError:
        module.fail_json(
            msg="Unable to run {}".format(' '.join(CMD)),
            **result
        )
    except Exception:
        module.fail_json(
            msg="Something unexpected occurred.",
            **result
        )

    module.exit_json(**result)


def main():
    run_module()


from ansible.module_utils.basic import *

main()
