import json
import logging

from .base import BaseSnitcher
from cloud_snitch.models import EnvironmentEntity
from cloud_snitch.models import DeviceEntity
from cloud_snitch.models import HostEntity
from cloud_snitch.models import InterfaceEntity
from cloud_snitch.models import MountEntity
from cloud_snitch.models import NameServerEntity
from cloud_snitch.models import PartitionEntity
from cloud_snitch.utils import complex_get

logger = logging.getLogger(__name__)

# Ansible key -> host kwarg map
_EASY_KEY_MAP = {
    'ansible_architecture': 'arcitecture',
    'ansible_bios_date': 'bios_date',
    'ansible_bios_version': 'bios_version',
    'ansible_kernel': 'kernel',
    'ansible_memtotal_mb': 'memtotal_mb',
    'ansible_fqdn': 'fqdn',
    'ansible_pkg_mgr': 'pkg_mgr',
    'ansible_processor_cores': 'processor_cores',
    'ansible_processor_count': 'processor_count',
    'ansible_processor_threads_per_core': 'processors_threads_per_core',
    'ansible_processor_vcpus': 'processor_vcpus',
    'ansible_python_version': 'python_version',
    'ansible_service_mgr': 'service_mgr',
    'ansible_selinux': 'selinux',
}

_COMPLEX_KEY_MAP = {
    'ansible_default_ipv4:address': 'default_ipv4_address',
    'ansible_default_ipv6:address': 'default_ipv6_address',
    'ansible_lsb:codename': 'lsb_codename',
    'ansible_lsb:description': 'lsb_description',
    'ansible_lsb:id': 'lsb_id',
    'ansible_lsb:major_release': 'lsb_major_release',
    'ansible_lsb:release': 'lsb_release',
    'ansible_python:executable': 'python_executable',
    'ansible_python:type': 'python_type',
    'ansible_version:full': 'ansible_version_full'
}

_MOUNT_KEY_MAP = {
    'mount': 'mount',
    'fstype': 'fstype',
    'size_total': 'size_total',
    'device': 'device'
}

_DEVICE_KEY_MAP = {
    'removable': 'removable',
    'rotational': 'rotational',
    'size': 'size'
}

_PARTITION_KEY_MAP = {
    'size': 'size',
    'start': 'start'
}

_INTERFACE_KEY_MAP = {
    'ansible_{}:active': 'active',
    'ansible_{}:macaddress': 'macaddress',
    'ansible_{}:mtu': 'mtu',
    'ansible_{}:promisc': 'promisc',
    'ansible_{}:device': 'device',
    'ansible_{}:ipv4:address': 'ipv4_address',
    'ansible_{}:ipv6:address': 'ipv6_address'
}


class HostSnitcher(BaseSnitcher):
    """Models path to update graph entities for an environment."""

    file_pattern = '^facts_(?P<hostname>.*).json$'

    def _update_interfaces(self, session, host, ansibledict):
        """Update host interfaces in graph.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param host: Host object
        :type host: HostEntity
        :param ansibledict: Ansible fact dict
        :type ansibledict: dict
        """
        interfaces = []

        # Obtain list of interfaces from ansible
        names = ansibledict.get('ansible_interfaces', [])
        for name in names:
            interfacedict = ansibledict.get('ansible_{}'.format(name))
            if interfacedict is None:
                continue

            interfacekwargs = {
                'device': name,
                'host': host.identity
            }

            for ansible_key, interface_key in _INTERFACE_KEY_MAP.items():
                ansible_key = ansible_key.format(name)
                val = complex_get(ansible_key, ansibledict)
                if val is not None:
                    interfacekwargs[interface_key] = val

            interface = InterfaceEntity(**interfacekwargs)
            interface.update(session, self.time_in_ms)
            interfaces.append(interface)
        host.interfaces.update(session, interfaces, self.time_in_ms)

    def _update_partitions(self, session, device, devicedict):
        """Update partitions of a device

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param device: device object
        :type device: DeviceEntity
        :param devicedict: Ansible fact dict
        :type devicedict: dict
        """
        partitions = []

        # Iterate over partition dicts from ansible
        ansiblepartitions = devicedict.get('partitions', {})
        for name, partitiondict in ansiblepartitions.items():
            partitionkwargs = {
                'name': name,
                'device': device.identity
            }

            # Create kwargs from key map
            for ansible_key, partition_key in _PARTITION_KEY_MAP.items():
                val = partitiondict.get(ansible_key)
                if val is not None:
                    partitionkwargs[partition_key] = val

            # Create the partition
            partition = PartitionEntity(**partitionkwargs)
            partition.update(session, self.time_in_ms)
            partitions.append(partition)

        # Update device -> partition edges.
        device.partitions.update(session, partitions, self.time_in_ms)

    def _update_devices(self, session, host, ansibledict):
        """Update devices for a host

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param host: Host object
        :type host: HostEntity
        :param ansibledict: Ansible fact dict
        :type ansibledict: dict
        """
        devices = []

        # Iterate over device dicts from ansible
        ansibledevices = ansibledict.get('ansible_devices', {})
        for name, devicedict in ansibledevices.items():
            devicekwargs = {
                'host': host.identity,
                'name': name
            }

            # Create kwargs from key map
            for ansible_key, device_key in _DEVICE_KEY_MAP.items():
                val = devicedict.get(ansible_key)
                if val is not None:
                    devicekwargs[device_key] = val

            device = DeviceEntity(**devicekwargs)
            device.update(session, self.time_in_ms)

            self._update_partitions(session, device, devicedict)

            devices.append(device)

        # Update host -> device edges
        host.devices.update(session, devices, self.time_in_ms)

    def _update_mounts(self, session, host, ansibledict):
        """Update mounts for a host.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param host: Host object
        :type host: HostEntity
        :param ansibledict: Ansible fact dict
        :type ansibledict: dict
        """
        mounts = []

        # Iterate over mount dicts from ansible
        ansiblemounts = ansibledict.get('ansible_mounts', [])
        for ansiblemount in ansiblemounts:
            mountkwargs = {'host': host.identity}

            # Create kwargs from key map
            for ansible_key, mount_key in _MOUNT_KEY_MAP.items():
                val = ansiblemount.get(ansible_key)
                if val is not None:
                    mountkwargs[mount_key] = val

            mount = MountEntity(**mountkwargs)
            mount.update(session, self.time_in_ms)
            mounts.append(mount)

        # Update host -> mounts edges.
        host.mounts.update(session, mounts, self.time_in_ms)

    def _update_nameservers(self, session, host, ansibledict):
        """Update nameservers for a host.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param host: Host object
        :type host: HostEntity
        :param ansibledict: Ansible fact dict
        :type ansibledict: dict
        """
        nameserver_list = complex_get('ansible_dns:nameservers', ansibledict)

        # Return early if no nameservers.
        if nameserver_list is None:
            return

        # Iterate over each nameserver in the list
        nameservers = []
        for nameserver_item in nameserver_list:
            nameserver = NameServerEntity(ip=nameserver_item)
            nameserver.update(session, self.time_in_ms)
            nameservers.append(nameserver)

        # Update edges from host to nameservers.
        host.nameservers.update(session, nameservers, self.time_in_ms)

    def _host_from_tuple(self, session, env, host_tuple):
        """Load hostdata from json file and create HostEntity instance.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param env: Environment entity hosts belong to.
        :type env: EnvironmentEntity
        :param host_tuple: (hostname, filename)
        :type host_tuple: tuple
        :returns: Host object
        :rtype: HostEntity
        """
        hostname, filename = host_tuple
        with open(filename, 'r') as f:
            fulldict = json.loads(f.read())
            fulldict = fulldict.get('data', {})

            # Start kwargs for making the host entity
            hostkwargs = {}

            # Remove anything not prefixed with 'ansible_'
            ansibledict = {}
            for k, v in fulldict.items():
                if k.startswith('ansible_'):
                    ansibledict[k] = v

            # Create properties that require little intervention
            for ansible_key, host_key in _EASY_KEY_MAP.items():
                val = ansibledict.get(ansible_key)
                if val is not None:
                    hostkwargs[host_key] = val

            # Create properties that can be found by path
            for complexkey, host_key in _COMPLEX_KEY_MAP.items():
                val = complex_get(complexkey, ansibledict)
                if val is not None:
                    hostkwargs[host_key] = val

        host = HostEntity(
            hostname=hostname,
            environment=env.identity,
            **hostkwargs
        )
        host.update(session, self.time_in_ms)

        # Update nameservers subgraph
        self._update_nameservers(session, host, ansibledict)

        # Update mounts subgraph
        self._update_mounts(session, host, ansibledict)

        # Update devices
        self._update_devices(session, host, ansibledict)

        # Update interfaces
        self._update_interfaces(session, host, ansibledict)

        return host

    def _snitch(self, session):
        """Orchestrates the updating of the hosts.

        Will first create/update any host entities.
        Will then version edges from environment to each host.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        """
        env = EnvironmentEntity(
            account_number=self.run.environment_account_number,
            name=self.run.environment_name
        )

        hosts = []

        # Update each host entity
        for host_tuple in self._find_host_tuples(self.file_pattern):
            host = self._host_from_tuple(session, env, host_tuple)
            hosts.append(host)

        # Return early if no hosts found
        if not hosts:
            return

        # Update edges from environment to each host.
        env.hosts.update(session, hosts, self.time_in_ms)
