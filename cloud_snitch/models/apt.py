import logging

from .base import VersionedEntity

logger = logging.getLogger(__name__)


class AptPackageEntity(VersionedEntity):
    """Model apt package nodes in the graph."""

    label = 'AptPackage'
    state_label = 'AptPackageState'
    identity_property = 'name_version'
    static_properties = [
        'name',
        'version'
    ]
    concat_properties = {
        'name_version': [
            'name',
            'version'
        ]
    }
