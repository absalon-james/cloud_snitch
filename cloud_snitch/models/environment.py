import logging

from base import VersionedEntity
from host import HostEntity
from gitrepo import GitRepoEntity
from uservar import UservarEntity

logger = logging.getLogger(__name__)


class EnvironmentEntity(VersionedEntity):
    """Model environment nodes in the graph."""

    label = 'Environment'
    state_label = 'EnvironmentState'
    identity_property = 'account_number_name'
    static_properties = [
        'account_number',
        'name',
    ]
    concat_properties = {
        'account_number_name': [
            'account_number',
            'name'
        ]
    }

    children = {
        'hosts': ('HAS_HOST', HostEntity),
        'gitrepos': ('HAS_GIT_REPO', GitRepoEntity),
        'uservars': ('HAS_USERVAR', UservarEntity)
    }
