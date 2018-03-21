import logging

from .base import VersionedEntity

logger = logging.getLogger(__name__)


class ConfigfileEntity(VersionedEntity):
    """Model a configuration file in the graph."""

    label = 'Configfile'
    state_label = 'ConfigfileState'
    identity_property = 'path_host'

    static_properties = [
        'path',
        'host',
        'name'
    ]
    state_properties = [
        'md5',
        'contents'
    ]
    concat_properties = {
        'path_host': [
            'path',
            'host'
        ]
    }
