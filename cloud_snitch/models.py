import logging
import pprint
import utils

logger = logging.getLogger(__name__)


class VersionedEntity(object):
    """Models an Entity with a versioned state,

    Properties are split into three categories:
    identity - how to uniquely identify the entity
    static_properties - properties that should not change and
        are not versioned
    state_properties - properties that should be versioned.

    The entity node will have a single identity node that will
    hold the identity and static properties.

    There will be multiple state nodes each with a relationship
    to the identity node. The relationships will contain
    `from` and `to` fields. The current state is the one
    where `to` is set to the end of time.
    """

    # Node label
    label = 'Label'
    state_label = 'LabelState'

    # How to identity entity uniquely
    identity_property = 'identity'

    # Properties we don't need to version
    static_properties = []

    # Properties we do need to version
    state_properties = []

    # Properties that are concatenations of other properties
    concat_properties = {}

    def __init__(self, **kwargs):
        """Init the versioned entity instance.

        This sets attributes according to property lists.
        """
        props = (self.state_properties + self.static_properties)
        props.append(self.identity_property)
        for prop in props:
            setattr(self, prop, kwargs.get(prop))

        for prop, cat_list in self.concat_properties.items():
            if not kwargs.get(prop):
                val = '-'.join([str(kwargs.get(p)) for p in cat_list])
                setattr(self, prop, val)

    @property
    def identity(self):
        """Get value of identity property.

        :returns: Value of the identity property
        :rtype: str
        """
        return getattr(self, self.identity_property, None)

    @classmethod
    def find(cls, tx, identity):
        """Finds an entity by identity.

        :param tx: neo4j transaction context
        :type tx: neo4j.v1.api.Transaction
        :param identity: Identity to find
        :type identity: str
        :returns: Instance of version entity or None
        :rtype: VersionedEntity|None
        """
        find = 'MATCH (n:{} {{ {}:${} }}) RETURN (n)'.format(
            cls.label,
            cls.identity_property,
            cls.identity_property
        )
        find_map = {}
        find_map[cls.identity_property] = identity
        record = tx.run(find, **find_map).single()
        if record is None:
            return record

        # Single returns a single itemed list.
        record = record[0]
        return cls(**({k: v for k, v in record.items()}))

    def _prop_clause(self, props):
        """Return info helpful to building property clauses.

        :param props: List of properties
        :type props: list
        :returns: Tuple of (prop_clause, prop_map)
        :rtype: tuple
        """
        parts = []
        part_fmt = '{}: ${}'
        prop_map = {}
        for prop in props:
            val = getattr(self, prop, None)
            if val is not None:
                parts.append(part_fmt.format(prop, prop))
                prop_map[prop] = val
        parts = ', '.join(parts)
        return parts, prop_map

    def _props_set_clause(self, node_variable, props):
        """Build clause for setting properties."""

        parts = []
        part_fmt = '{}.{} = ${}'
        prop_map = {}
        for prop in props:
            val = getattr(self, prop, None)
            if val is not None:
                parts.append(part_fmt.format(node_variable, prop, prop))
                prop_map[prop] = val
        parts = ', '.join(parts)
        return parts, prop_map

    def _update_state(self, tx):
        """Close current state and create a new state if data differs.

        :param tx: neo4j transaction context.
        :type tx: neo4j.v1.api.Transaction
        """
        if not self.state_properties:
            return

        parts, prop_map = self._prop_clause(self.state_properties)

        # Match current state
        cypher = """\
            MATCH (a:{} {{ {}: $identity}})
                -[r:HAS_STATE {{to: $state_rel_to}}]
                ->(currentState:{})
            RETURN currentState
        """
        cypher = cypher.format(
            self.label,
            self.identity_property,
            self.state_label
        )
        resp = tx.run(cypher, state_rel_to=utils.EOT, identity=self.identity)
        record = resp.single()
        if record is None:
            current_properties = {}
        else:
            current_properties = {k: v for k, v in record[0].items()}

        # Determine if new state is different from current
        dirty = False
        for prop in self.state_properties:
            if current_properties.get(prop) != prop_map.get(prop):
                dirty = True

        if dirty:
            logger.debug("Data is dirty, making a new state.")
            now = utils.milliseconds_now()

            # Mark current state as old
            cypher = """
                MATCH (c:{} {{ {}:$identity }})
                   -[r1:HAS_STATE {{to: $EOT}}]
                   ->(currentState:{})
                SET r1.to = $now
            """
            cypher = cypher.format(
                self.label,
                self.identity_property,
                self.state_label
            )
            tx.run(cypher, identity=self.identity, now=now, EOT=utils.EOT)

            # Create relationship
            prop_map.update({
                'EOT': utils.EOT,
                'now': now,
                'identity': self.identity
            })
            cyper = """
                MATCH (s:{} {{ {}:$identity }})
                CREATE (s)
                    -[r2:HAS_STATE {{to: $EOT, from: $now }}]
                    ->(newState:{} {{ {} }})
                RETURN newState
            """
            cypher = cyper.format(
                self.label,
                self.identity_property,
                self.state_label,
                parts
            )
            logger.debug('Update state cypher:')
            logger.debug(cypher)
            logger.debug("With params:\n{}".format(pprint.pformat(prop_map)))
            resp = tx.run(cypher, **prop_map)

    def update(self, tx):
        """Update the entity in the graph.

        :param tx: neo4j transaction context
        :type tx: neo4j.v1.api.Transaction
        """

        static_props = {}
        for prop in self.static_properties:
            val = getattr(self, prop, None)
            if val is not None:
                static_props[prop] = val

        parts, prop_map = self._props_set_clause('n', self.static_properties)

        if prop_map:
            create_clause = (
                'ON CREATE SET  n.created_at = timestamp(), {}'.format(parts)
            )
            update_clause = 'ON MATCH SET {}'.format(parts)
        else:
            create_clause = 'ON CREATE SET  n.created_at = timestamp()'
            update_clause = ''

        cypher = """
            MERGE (n:{} {{ {}:$identity }})
            {}
            {}
            RETURN n
        """
        cypher = cypher.format(
            self.label,
            self.identity_property,
            create_clause,
            update_clause
        )
        resp = tx.run(cypher, identity=self.identity, **prop_map)
        logger.debug(resp)
        self._update_state(tx)

    def touch(self, tx):
        """Ensures an identity node exists without worrying about state.

        :param tx: neo4j transaction context
        :type tx: neo4j.v1.api.Transaction
        """
        cypher = """
            MERGE (n:{} {{ {}:$identity }})
            ON CREATE SET n.created_at = timestamp()
            RETURN n
        """
        cypher = cypher.format(
            self.label,
            self.identity_property,
        )
        resp = tx.run(cypher, identity=self.identity)
        logger.debug(resp)


class VersionedEdgeSet(object):

    def __init__(self, name, source, dest_type):
        """Init the versioned edge set

        :param name: Name of the relation ship. example: HAS_HOST
        :type name: str
        :param source: Source Object. All edges in the set start here
        :type source: VersionedEntity
        :param dest_type: Type of the end of the the edges in the set
        :type dest_type: class
        """
        self.name = name
        self.source = source
        self.dest_type = dest_type

    def update(self, tx, edges):
        """Update the versioned edge set

        First match all edges from source to dest_type entities that
        are current(the `to` field is set to end of time).

        Determine the edges that are no longer current and mark them with
        a `to` set to now

        Create the edges that need to be added.
        """
        now = utils.milliseconds_now()
        new_edges = set([e.identity for e in edges])

        # Match existing edges
        cypher = """\
            MATCH (s:{} {{ {}:$identity }})-[r:{} {{to:$time}}]->(d:{})
            RETURN d.{}
        """
        cypher = cypher.format(
            self.source.label,
            self.source.identity_property,
            self.name,
            self.dest_type.label,
            self.dest_type.identity_property
        )
        logger.debug("Finding current edges:")
        logger.debug(cypher)
        resp = tx.run(
            cypher,
            identity=self.source.identity,
            time=utils.EOT
        )

        logger.debug("New edges: {}".format(new_edges))

        current_edges = set()
        key = 'd.{}'.format(self.dest_type.identity_property)
        for record in resp:
            current_edges.add(record[key])

        logger.debug("Current edges: {}".format(current_edges))

        # Set `to` on edges that are no longer current
        old_edges = current_edges - new_edges
        logger.debug("Old edges: {}".format(old_edges))

        for old_identity in old_edges:
            cypher = """
                MATCH (s:{} {{ {}:$srcIdentity}})
                MATCH (d:{} {{ {}:$destIdentity}})
                MATCH (s)-[r:{} {{ to: $eot }}]->(d)
                SET r.to = $to
            """
            cypher = cypher.format(
                self.source.label,
                self.source.identity_property,
                self.dest_type.label,
                self.dest_type.identity_property,
                self.name
            )
            logger.debug("Marking {} --> {} as old".format(
                self.source.identity,
                old_identity)
            )
            logger.debug(cypher)
            tx.run(
                cypher,
                srcIdentity=self.source.identity,
                destIdentity=old_identity,
                eot=utils.EOT,
                to=now
            )

        # Merge in new edges
        add_edges = new_edges - current_edges
        for add_identity in add_edges:
            cypher = """
                MATCH (s:{} {{ {}:$srcIdentity }})
                MATCH (d:{} {{ {}:$destIdentity }})
                MERGE (s)-[r:{} {{ to: $to }}]->(d)
                ON CREATE SET r.from = $frm
            """
            cypher = cypher.format(
                self.source.label,
                self.source.identity_property,
                self.dest_type.label,
                self.dest_type.identity_property,
                self.name
            )
            logger.debug("Creating edge {} --> {}:".format(
                self.source.identity,
                add_identity)
            )
            logger.debug(cypher)
            tx.run(
                cypher,
                srcIdentity=self.source.identity,
                destIdentity=add_identity,
                frm=now,
                to=utils.EOT
            )


class EnvironmentEntity(VersionedEntity):
    """Model environment nodes in the graph."""

    label = 'Environment'
    state_label = 'EnvironmentState'
    identity_property = 'account_number_name'
    static_properties = ['account_number', 'name']
    concat_properties = {
        'account_number_name': [
            'account_number',
            'name'
        ]
    }


class HostEntity(VersionedEntity):
    """Model host nodes in the graph."""

    label = 'Host'
    state_label = 'HostState'
    identity_property = 'hostname'

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


class NameServerEntity(VersionedEntity):
    """Model a name server node in the graph."""

    label = 'NameServer'
    state_label = 'NameServerState'
    identity_property = 'ip'


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
