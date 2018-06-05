import os

from pwsafe.comp import PasswordSafeComp
from ansible.plugins.vars import BaseVarsPlugin

__metaclass__ = type

DOCUMENTATION = '''
    vars: pwsafe_vars
    version_added: "2.4"
    short_description: In charge of loading pwsafe vars
    description:
        - Slurps in variables from password safe
        - Uses environment variables SSO_USERNAME and SSO_PASSWORD and PWSAFE_PROJECT for login credentials
        - Uses the credential's "prerequisites" field to map to variable names within ansible.
        - Credentials within the project are turned into variables of pwsafe_<<prerequisites>>_username and pwsafe_<<prerequisites>>_password
    notes:
        - Not sure if this works
'''


PWSAFE_CACHE = {
    "run": False,
    "data": {}
}


class VarsModule(BaseVarsPlugin):

    def get_vars(self, loader, path, entities, cache=True):
        ''' loads vars from password safe.
            Since the data fetched from password safe is all or nothing, it's
            safe to assume that we can just return the single result if we
            have a cache hit. This way we only hit the API once.
        '''

        if PWSAFE_CACHE["run"] is True and cache is True:
            return PWSAFE_CACHE["data"]

        sso_username = os.environ.get('SSO_USERNAME')
        sso_password = os.environ.get('SSO_PASSWORD')
        pwsafe_project = os.environ.get('PWSAFE_PROJECT')

        if None in [sso_username, sso_password, pwsafe_project]:
            msg = ("Please export env vars: "
                   "SSO_USERNAME, SSO_PASSWORD, and PWSAFE_PROJECT.")
            raise Exception(msg)


        pwsafe_client = PasswordSafeComp(sso_username, sso_password).client
        creds = pwsafe_client.get_creds(pwsafe_project).json()
        creds = [cred.get('credential') for cred in creds]
        pwsafe_vars = {}
        for cred in creds:
            prerequisites = cred.get('prerequisites')
            if prerequisites:
                if cred.get('username'):
                    key = "pwsafe_%s_username" % prerequisites
                    value = cred.get('username')
                    pwsafe_vars[key] = value
                if cred.get('password'):
                    key = "pwsafe_%s_password" % prerequisites
                    value = cred.get('password')
                    pwsafe_vars[key] = value

        PWSAFE_CACHE["run"] = True
        PWSAFE_CACHE["data"] = pwsafe_vars
        return pwsafe_vars
