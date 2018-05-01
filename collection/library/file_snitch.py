#!/usr/bin/python

import glob
import re
import StringIO

DOCUMENTATION = '''
---
module: file_snitch

short_description: Gathers configuration files.

version_added: "2.1.6"

description:
    - "Pulls configuration files from a host"
    - "Matches files according to list."

extends_documentation_fragment:
    - azure

author:
    - James Absalon
'''

RETURN = '''
payload:
    description: |
       Dict keyed matching file name. The value of each will be the contents
       of the file.
    type: dict
doctype:
    description: Type of document. Will always be 'file_dict'
    type: str
'''

EASY_FLAGS = [
    'token',
    'key',
    'password',
    'pass',
    'pwd',
    'passwd',
    'passwrd',
    'secret'
]

left = '^(?P<left>[^:=]*\w+)'
op = '(?P<op>(\s*)(=|:)(\s*))'

EASY_ASSIGNMENT_EXP = re.compile('{}{}(?P<right>.+)$'.format(
    left,
    op
))

right = '(?P<protouser>[\w\+]+://[\w]+:)(?P<password>[\w]+)(?P<rest>@.*)'
URL_EXP = re.compile('{}{}{}'.format(left, op, right))


MAX_FILE_SIZE = 1024 * 16


class FileTooLargeError(Exception):
    pass


def redact(part):
    """Redacts a part of information.

    :param part: Part of a string to redact
    :type part: str
    :returns: Redacted string
    :rtype: str
    """
    return '*' * 8


def mask_line(line):
    """Make best guess at censoring sensitive information.

    :param line: Line to mask
    :type line: str
    :returns: Censored line,
    :rtype: str
    """
    # Check for match on an assignment operation
    match = EASY_ASSIGNMENT_EXP.search(line)
    if match:
        left = match.group('left').lower()
        if any([left.endswith(flag) for flag in EASY_FLAGS]):
            return "{}{}{}".format(
                match.group('left'),
                match.group('op'),
                redact(match.group('right')) + '\n'
            )
    match = URL_EXP.search(line)
    if match:
        return '{}{}{}{}{}'.format(
            match.group('left'),
            match.group('op'),
            match.group('protouser'),
            redact(match.group('password')),
            match.group('rest') + '\n'
        )
    return line


def get_file(filename):
    """Get contents of a file.

    :param filename: Name of the file
    :type filename: str
    :returns: Contents of file
    :rtype: str
    """
    # Check the file size.
    size = os.path.getsize(filename)
    if size > MAX_FILE_SIZE:
        raise FileTooLargeError(
            '{} exceeds the max file size of {} bytes.'
            .format(filename, MAX_FILE_SIZE)
        )

    # Read the file and make an attempt to mask sensitive information.
    with open(filename, 'r') as f:
        s = StringIO.StringIO()
        for line in f.readlines():
            s.write(mask_line(line))
        return s.getvalue()


def run_module():
    module_args = dict(
        file_list=dict(required=False, type='list'),
    )

    result = dict(
        changed=False,
        payload={},
        doctype='file_dict'
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    filenames = []
    for t in module.params.get('file_list', []):
        filenames += glob.glob(t)

    for filename in filenames:
        try:
            result['payload'][filename] = get_file(filename)
        except IOError:
            pass
        except FileTooLargeError:
            toolarge = result.setdefault('files_too_large', [])
            toolarge.append(filename)

    module.exit_json(**result)


def main():
    run_module()

from ansible.module_utils.basic import *

main()
