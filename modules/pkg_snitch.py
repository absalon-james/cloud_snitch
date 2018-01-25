#!/usr/bin/python

DOCUMENTATION = '''
---
module: pkg_snitch

short_description: Gathers data on what packages are installed.

version_added: "2.1.6"

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

import subprocess

from ansible.module_utils.basic import AnsibleModule

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
    for i in xrange(5, len(lines)):
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
    # define the available arguments/parameters that a user can pass to
    # the module
    module_args = dict(
        #name=dict(type='str', required=True),
        #new=dict(type='bool', required=False, default=False)
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # change is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
        payload=[],
        doctype='dpkg_list'
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications

    # This module is read only.
    #if module.check_mode:
    #    return result

    # manipulate or modify the state as needed (this is going to be the
    # part where your module will do what it needs to do)
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

    # This module will allways be read only
    #if module.params['new']:
    #    result['changed'] = True

    # during the execution of the module, if there is an exception or a
    # conditional state that effectively causes a failure, run
    # AnsibleModule.fail_json() to pass in the message and the result
    # @TODO - Check Failing
    #if module.params['name'] == 'fail me':
    #    module.fail_json(msg='You requested this to fail', **result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()
