import argparse
import json
import os
import subprocess

parser = argparse.ArgumentParser(
    description='Prepopulate host vars for uam dynamic inventory.'
)

parser.add_argument(
    '--inventory',
    type=str,
    help='Location of uam dynamic inventory.',
    default='/etc/ansible/inventory/inventory.py'
)

parser.add_argument(
    '--hostvars_dir',
    type=str,
    help='Location of directory to contain host_vars.',
    default='/etc/ansible/inventory/host_vars'
)

snitches = [
    'pkg',
    'pip',
    'facts',
    'config',
    'git',
    'uservars'
]


def inventory_json(inventory_file):
    """Execute uam's dynamic inventory script and capture stdout.

    :param inventory_file: Location of uam dynamic inventory script
    :type inventory_file: str
    """
    call_args = ['python', inventory_file]
    output = subprocess.check_output(call_args)
    return json.loads(output)


def generate_host(name, data, hostvars_dir):
    """Generate a host_vars file for a host.

    :param name: Name of the host. usually <customer_name>-<environment_name>
    :type name: str
    :param data: Map of key value pairs describing the host
    :type data: dict
    :param hostvars_dir: Location of host_vars dir to write a yml file
    :type hostvars_dir: str
    """
    customer_name, environment_name = name.rsplit('-', 1)

    filename = os.path.join(hostvars_dir, '{}.yml'.format(name))
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            f.write(
                'cloud_snitch_environment_account_number: '
                '"{{ core_account }}"\n'
            )
            f.write(
                'cloud_snitch_environment_name: {}-{}\n'
                .format(customer_name, environment_name)
            )
            for s in snitches:
                f.write('#cloud_snitch_{}_enabled: False\n'.format(s))


def iterate_hosts(inventory, hostvars_dir):
    """Iterate over hosts in the dynamic inventory.

    :param inventory: Inventory from the dynamic inventory.
    :type inventory: dict
    :param hostvars_dir: Location of host_vars dir to write yml files to.
    :type hostvars_dir: str
    """
    hostvars = inventory.get('_meta', {}).get('hostvars', {})
    for name, data in hostvars.items():
        generate_host(name, data, hostvars_dir)


if __name__ == '__main__':
    args = parser.parse_args()
    inventory = inventory_json(args.inventory)
    iterate_hosts(inventory, args.hostvars_dir)
