import logging

from .base import VersionedEntity

logger = logging.getLogger(__name__)


class UservarEntity(VersionedEntity):
    """Models a user variable."""

    label = 'Uservar'
    state_label = 'UservarState'

    identity_property = 'name_environment'
    static_properties = [
        'name',
        'environment'
    ]
    state_properties = [
        'value'
    ]
    concat_properties = {
        'name_environment': [
            'name',
            'environment'
        ]
    }
