from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import git
import os
import yaml

from git.exc import NoSuchPathError
from git.exc import InvalidGitRepositoryError
from git.refs.remote import RemoteReference
from git.refs.tag import TagReference

# Try the ansible 2.1+ style first
try:
    from ansible.plugins.action import ActionBase
    OLD = False

# Fallback to the old style
except ImportError:
    from ansible.runner.return_data import ReturnData
    OLD = True

    class ActionBase(object):
        def __init__(self, runner):
            self.runner = runner

_MERGE_BASE_REF_TYPES = [RemoteReference, TagReference]


# Attempt to load configuration
conf_file = os.environ.get(
    'CLOUD_SNITCH_CONF_FILE',
    '/etc/cloud_snitch/cloud_snitch.yml')
with open(conf_file, 'r') as f:
    settings = yaml.load(f.read())

_REPO_LIST = settings.get('git_repo_list', [])


class ActionModule(ActionBase):

    def get_repo_tuples(self, repo_path_list):
        """Iterate over list of paths to find matching repos.

        :params repo_path_list: List of repo paths to search
        :type repo_path: list
        :returns: Matching path and git repo objects
        :rtype: list
        """
        repos = []
        for repo_path in repo_path_list:
            try:
                repos.append((repo_path, git.Repo(repo_path)))
            except NoSuchPathError:
                pass
            except InvalidGitRepositoryError:
                pass
        return repos

    def get_branch_name(self, repo):
        """Get repo branch name.

        Not all repos will have an active branch, such as ones
        whose HEAD is detached.

        :param repo: Repo object
        :type repo: git.Repo
        :returns: Name of the active branch or None
        :rtype: str
        """
        try:
            name = repo.active_branch.name
        except TypeError:
            name = None
        return name

    def get_merge_base_ref(self, repo):
        """Get ref that is starting point for any differences.

        :param repo: Repo object
        :type repo: git.Repo
        :returns: Matching merge base reference.
        :rtype: git.refs.reference.Reference
        """
        ref_map = {str(r.commit): r for r in repo.refs}
        for commit in repo.iter_commits('HEAD'):
            ref = ref_map.get(str(commit))
            types = [isinstance(ref, t) for t in _MERGE_BASE_REF_TYPES]
            if ref and any(types):
                return ref
        return None

    def get_repo_data(self, repo_paths):
        """Get repo data for a list of repo paths.

        :param repo_paths: List of paths indication locations of repos
        :type repo_paths: list
        :returns: List of dicts describing repo states
        :rtype: list
        """
        repo_tuples = self.get_repo_tuples(repo_paths)
        results = []

        for path, repo in repo_tuples:
            # Build remotes dictionary
            remote_dict = dict()
            for remote in repo.remotes:
                remote_dict[remote.name] = list(remote.urls)

            # Build Merge base dictionary
            merge_base_ref = self.get_merge_base_ref(repo)
            merge_base_dict = None
            if merge_base_ref:
                merge_base_diff = repo.commit().diff(
                    merge_base_ref.commit,
                    create_patch=True
                )
                merge_base_dict = dict(
                    name=str(merge_base_ref),
                    diff=[str(d) for d in merge_base_diff]
                )

            # Get working tree differences.
            index_diff = repo.index.diff(None, create_patch=True)

            # Build rest of repo information
            repo_dict = dict(
                active_branch_name=self.get_branch_name(repo),
                is_detached=repo.head.is_detached,
                remotes=remote_dict,
                path=path,
                head_sha=repo.head.object.hexsha,
                merge_base=merge_base_dict,
                working_tree=dict(
                    is_dirty=repo.is_dirty(),
                    untracked_files=repo.untracked_files,
                    diff=[str(d) for d in index_diff]
                )
            )
            results.append(repo_dict)
        return results

    def run_old(
        self,
        conn,
        tmp,
        module_name,
        module_args,
        inject,
        complex_args=None,
        **kwargs
    ):
        """Run the old version."""
        result = dict(changed=False, payload=None, doctype='gitrepos')
        # Only save data if cloud snitch is enabled
        if not os.environ.get('CLOUD_SNITCH_ENABLED'):
            return ReturnData(conn=conn, result=result)

        result['payload'] = self.get_repo_data(_REPO_LIST)
        return ReturnData(conn=conn, result=result)

    def run_new(self, tmp=None, task_vars=None):
        """Run the new style."""
        result = super(ActionModule, self).run(tmp, task_vars)
        result.update(changed=False, payload=None, doctype='gitrepos')

        # Only save data if cloud snitch is enabled
        if not os.environ.get('CLOUD_SNITCH_ENABLED'):
            return result

        if task_vars is None:
            task_vars = {}
        result['payload'] = self.get_repo_data(_REPO_LIST)
        return result

    def run(self, *args, **kwargs):
        """Run the action module."""
        if OLD:
            return self.run_old(*args, **kwargs)
        else:
            return self.run_new(*args, **kwargs)
