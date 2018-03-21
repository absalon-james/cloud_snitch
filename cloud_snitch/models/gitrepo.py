import logging

from .base import VersionedEntity

logger = logging.getLogger(__name__)


class GitUntrackedFileEntity(VersionedEntity):
    """Models an untracked file in a gitrepo."""

    label = 'GitUntrackedFile'
    state_label = 'GitUntrackedFile'
    identity_property = 'path'


class GitUrlEntity(VersionedEntity):
    """Models a git repo url."""

    label = 'GitUrl'
    state_label = 'GitUrlState'
    identity_property = 'url'


class GitRemoteEntity(VersionedEntity):
    """Models a git repo remote."""

    label = 'GitRemote'
    state_label = 'GitRemoteState'
    identity_property = 'name_repo'
    static_properties = [
        'name',
        'repo'
    ]
    concat_properties = {
        'name_repo': [
            'name',
            'repo'
        ]
    }

    children = {
        'urls': ('HAS_GIT_URL', GitUrlEntity)
    }


class GitRepoEntity(VersionedEntity):
    """Models a git repo."""

    label = 'GitRepo'
    state_label = 'GitRepoState'
    identity_property = 'path_environment'
    static_properties = [
        'path',
        'environment'
    ]
    state_properties = [
        'active_branch_name',
        'head_sha',
        'is_detached',
        'working_tree_dirty',
        'working_tree_diff_md5',
        'merge_base_name',
        'merge_base_diff_md5'
    ]
    concat_properties = {
        'path_environment': [
            'path',
            'environment'
        ]
    }

    children = {
        'untrackedfiles': ('HAS_UNTRACKED_FILE', GitUntrackedFileEntity),
        'remotes': ('HAS_GIT_REMOTE', GitRemoteEntity)
    }
