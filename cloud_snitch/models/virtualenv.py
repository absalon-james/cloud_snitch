import logging

from .base import VersionedEntity

logger = logging.getLogger(__name__)


class PythonPackageEntity(VersionedEntity):
    """Model pythonpackage nodes in the graph."""

    label = 'PythonPackage'
    state_label = 'PythonPackageState'
    identity_property = 'name_version'
    static_properties = ['name', 'version']
    concat_properties = {
        'name_version': [
            'name',
            'version'
        ]
    }


class VirtualenvEntity(VersionedEntity):
    """Model virtualenv nodes in the graph."""

    label = 'Virtualenv'
    state_label = 'VirtualenvState'
    identity_property = 'path_host'
    static_properties = [
        'path',
        'host'
    ]
    concat_properties = {
        'path_host': [
            'path',
            'host'
        ]
    }

    children = {
        'pythonpackages': ('HAS_PYTHON_PACKAGE', PythonPackageEntity)
    }
