import logging

from .base import VersionedEntity
from .apt import AptPackageEntity
from .configfile import ConfigfileEntity
from .virtualenv import VirtualenvEntity

logger = logging.getLogger(__name__)


class NameServerEntity(VersionedEntity):
    """Model a name server node in the graph."""

    label = 'NameServer'
    state_label = 'NameServerState'
    identity_property = 'ip'


class PartitionEntity(VersionedEntity):
    """Model a partition on a device in the graph."""

    label = 'Partition'
    state_label = 'PartitionState'
    identity_property = 'name_device'

    static_properties = [
        'name',
        'device'
    ]

    state_properties = [
        'size',
        'start'
    ]

    concat_properties = {
        'name_device': [
            'name',
            'device'
        ]
    }


class DeviceEntity(VersionedEntity):
    """Model a device node in the graph."""

    label = 'Device'
    state_label = 'DeviceState'
    identity_property = 'name_host'

    static_properties = [
        'name',
        'host',
    ]

    state_properties = [
        'removable',
        'rotational',
        'size'
    ]

    concat_properties = {
        'name_host': [
            'name',
            'host'
        ]
    }

    children = {
        'partitions': ('HAS_PARTITION', PartitionEntity)
    }


class MountEntity(VersionedEntity):
    """Model a mount node in the graph."""

    label = 'Mount'
    state_label = 'MountState'
    identity_property = 'mount_host'

    static_properties = [
        'mount',
        'host',
    ]

    state_properties = [
        'device',
        'size_total',
        'fstype'
    ]

    concat_properties = {
        'mount_host': [
            'mount',
            'host'
        ]
    }


class InterfaceEntity(VersionedEntity):
    """Model interface nodes in the graph."""

    label = 'Interface'
    state_label = 'InterfaceState'
    identity_property = 'device_host'

    static_properties = [
        'device',
        'host'
    ]

    state_properties = [
        'active',
        'ipv4_address',
        'ipv6_address',
        'macaddress',
        'mtu',
        'promisc',
        'type'
    ]

    concat_properties = {
        'device_host': [
            'device',
            'host'
        ]
    }


class HostEntity(VersionedEntity):
    """Model host nodes in the graph."""

    label = 'Host'
    state_label = 'HostState'
    identity_property = 'hostname_environment'

    static_properties = [
        'hostname',
        'environment'
    ]

    concat_properties = {
        'hostname_environment': [
            'hostname',
            'environment'
        ]
    }

    state_properties = [
        'architecture',
        'bios_date',
        'bios_version',
        'default_ipv4_address',
        'default_ipv6_address',
        'kernel',
        'memtotal_mb',
        'lsb_codename',
        'lsb_description',
        'lsb_id',
        'lsb_major_release',
        'lsb_release',
        'fqdn',
        'pkg_mgr',
        'processor_cores',
        'processor_count',
        'processor_threads_per_core',
        'processor_vcpus',
        'python_executable',
        'python_version',
        'python_type',
        'service_mgr',
        'selinux',
        'ansible_version_full'
    ]

    children = {
        'aptpackages': ('HAS_APT_PACKAGE', AptPackageEntity),
        'virtualenvs': ('HAS_VIRTUALENV', VirtualenvEntity),
        'configfiles': ('HAS_CONFIG_FILE', ConfigfileEntity),
        'nameservers': ('HAS_NAMESERVER', NameServerEntity),
        'interfaces': ('HAS_INTERFACE', InterfaceEntity),
        'mounts': ('HAS_MOUNT', MountEntity),
        'devices': ('HAS_DEVICE', DeviceEntity)
    }
