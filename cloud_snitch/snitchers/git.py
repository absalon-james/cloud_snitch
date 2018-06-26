import hashlib
import json
import logging
import os

from .base import BaseSnitcher
from cloud_snitch.models import EnvironmentEntity
from cloud_snitch.models import GitRepoEntity
from cloud_snitch.models import GitRemoteEntity
from cloud_snitch.models import GitUrlEntity
from cloud_snitch.models import GitUntrackedFileEntity

logger = logging.getLogger(__name__)


class GitSnitcher(BaseSnitcher):
    """Models the following path env -> gitrepo -> remotename -> url"""

    def _update_untracked_file(self, session, path):
        """Update a untracked file in a graph

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param path: Path local to the repo of the untracked file
        :type path: str
        :returns: Untracked file object
        :rtype: GitUntrackedFileEntity
        """
        untracked = GitUntrackedFileEntity(path=path)
        untracked.update(session, self.time_in_ms)
        return untracked

    def _update_url(self, session, urlstr):
        """Update a git url in a graph.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param urlstr: Url to update
        :type urlstr: str
        """
        url = GitUrlEntity(url=urlstr)
        url.update(session, self.time_in_ms)
        return url

    def _update_remote(self, session, repo, name, urllist):
        """Updates git remotes for a git repo.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param repo: Source repo
        :type repo: GitRepoEntity
        :param gitrepo: source git repo
        :type gitrepo: GitRepoEntity
        :param name: Name of the remote (origin, upstream, etc)
        :type name: str
        :param urllist: List of urls
        :type urllist: list
        """
        remote = GitRemoteEntity(name=name, repo=repo.identity)
        remote.update(session, self.time_in_ms)

        urls = []
        for url in urllist:
            urls.append(self._update_url(session, url))

        remote.urls.update(session, urls, self.time_in_ms)
        return remote

    def _update_gitrepo(self, session, env, repodict):
        """Updates gitrepo information in graph.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param env: Parent environment
        :type env: EnvironmentEntity
        :param repodict: git repo dict.
        :type pkg: dict
        :returns: GitRepo object
        :rtype: GitRepoEntity
        """
        # Calculate md5 of merge base diff
        merge_base_diff = repodict['merge_base']['diff']
        if not merge_base_diff:
            merge_base_diff_md5 = None
        else:
            m = hashlib.md5()
            m.update(''.join(merge_base_diff).encode('utf-8'))
            merge_base_diff_md5 = m.hexdigest()

        # Calculate md5 of working_tree_diff
        working_tree_diff = repodict['working_tree']['diff']
        if not working_tree_diff:
            working_tree_diff_md5 = None
        else:
            m = hashlib.md5()
            m.update(''.join(working_tree_diff).encode('utf-8'))
            working_tree_diff_md5 = m.hexdigest()

        # Make instance of the git repo
        gitrepo = GitRepoEntity(
            environment=env.identity,
            active_branch_name=repodict.get('active_branch_name'),
            head_sha=repodict.get('head_sha'),
            is_detached=repodict.get('is_detached'),
            merge_base_name=repodict['merge_base']['name'],
            merge_base_diff_md5=merge_base_diff_md5,
            path=repodict.get('path'),
            working_tree_dirty=repodict['working_tree']['is_dirty'],
            working_tree_diff_md5=working_tree_diff_md5
        )
        gitrepo.update(session, self.time_in_ms)

        # Update all remotes.
        remotes = []
        for name, urls in repodict.get('remotes', {}).items():
            remotes.append(self._update_remote(session, gitrepo, name, urls))
        gitrepo.remotes.update(session, remotes, self.time_in_ms)

        # Update untracked files
        untracked = []
        for path in repodict['working_tree'].get('untracked_files', []):
            untracked.append(self._update_untracked_file(session, path))

        gitrepo.untrackedfiles.update(session, untracked, self.time_in_ms)
        return gitrepo

    def _snitch(self, session):
        """Orchestrates the creation of the environment.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        """
        # Load saved git data
        try:
            filename = os.path.join(self._basedir(), 'gitrepos.json')
            with open(filename, 'r') as f:
                gitdata = json.loads(f.read())
        except IOError:
            logger.info('No data for git could be found.')
            return

        # Let model compute environment identity
        env = EnvironmentEntity(
            account_number=gitdata['environment']['account_number'],
            name=gitdata['environment']['name']
        )
        identity = env.identity

        # Try to locate environment by identity
        env = EnvironmentEntity.find(session, identity)
        if env is None:
            logger.warning(
                'Unable to locate environment {}.'.format(identity)
            )
            return

        # Iterate over each git repo
        gitrepos = []
        for gitdict in gitdata.get('data', []):
            gitrepo = self._update_gitrepo(session, env, gitdict)
            gitrepos.append(gitrepo)

        # Update edges
        env.gitrepos.update(session, gitrepos, self.time_in_ms)
