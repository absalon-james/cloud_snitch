import logging
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
                logger.debug([kwargs.get(p, '') for p in cat_list])
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

    def _create_state(self, tx):
        """Create a new state with state properties.

        :param tx: neo4j transaction context.
        :type tx: neo4j.v1.api.Transaction
        """
        # Create state
        if not self.state_properties:
            return
        parts, prop_map = self._prop_clause(self.state_properties)

        # Create relationship
        prop_map.update({
            'state_rel_to': utils.EOT,
            'state_rel_from': utils.milliseconds_now(),
            'identity': self.identity
        })
        cyper = """\
            MATCH (s:{} {{ {}:$identity }})
            CREATE (s)-[:HAS_STATE {{to: $state_rel_to, from: $state_rel_from }}]->(newState:{} {{ {} }})
            RETURN newState
        """
        cypher = cyper.format(
            self.label,
            self.identity_property,
            self.state_label,
            parts
        )
        logger.debug("Create state cypher:")
        logger.debug(cypher)
        resp = tx.run(cypher, **prop_map)
        if resp.single() is None:
            raise Exception('Unable to create new state')


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
            MATCH (a:{} {{ {}: $identity}})-[r:HAS_STATE {{to: $state_rel_to}}]->(currentState:{})
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

            # Create relationship
            prop_map.update({
                'EOT': utils.EOT,
                'now': now,
                'state_rel_to': utils.EOT,
                'identity': self.identity
            })
            cyper = """\
                MATCH (c:{} {{ {}:$identity }})-[r1:HAS_STATE {{to: $EOT}}]->(currentState:{})
                SET r1.to = $now
                WITH r1
                MATCH (s:{} {{ {}:$identity }})
                CREATE (s)-[r2:HAS_STATE {{to: $EOT, from: $now }}]->(newState:{} {{ {} }})
                RETURN newState
            """
            cypher = cyper.format(
                self.label,
                self.identity_property,
                self.state_label,
                self.label,
                self.identity_property,
                self.state_label,
                parts
            )
            logger.debug('Update state cypher:')
            logger.debug(cypher)
            resp = tx.run(cypher, **prop_map)

    def create(self, tx):
        """Create the entity.

        Create entity with static properties set
        Create entity state with  state properties.

        @TODO - Check for errors on create

        :param tx: neo4j transaction context.
        :type tx: neo4j.v1.api.Transaction

        """
        # Create identity node first
        props = self.static_properties + [self.identity_property]

        prop_parts = []
        prop_map = {}
        for prop in props:
            val = getattr(self, prop, None)
            if val is not None:
                prop_parts.append('{}: ${}'.format(prop, prop))
                prop_map[prop] = val

        prop_parts = ', '.join(prop_parts)
        cypher = 'create (n:{} {{ {} }}) RETURN (n)'.format(
            self.label,
            prop_parts
        )
        resp = tx.run(cypher, **prop_map)
        if resp.single() is None:
            raise Exception('Unable to complete create of identity node.')

        # Create state node next
        self._create_state(tx)

    def update(self, tx):
        exists = self.find(tx, self.identity)
        if exists is None:
            logger.debug("{} does not exist. creating ...".format(self.label))
            record = self.create(tx)
        else:
            self._update_state(tx)


class VersionedEdgeSet(object):

    def __init__(self, name, source, dest_type):
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
            logger.debug("Marking {} --> {} as old".format(self.source.identity, old_identity))
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
            logger.debug("Creating edge {} --> {}:".format(self.source.identity, add_identity))
            logger.debug(cypher)
            tx.run(
                cypher,
                srcIdentity=self.source.identity,
                destIdentity=add_identity,
                frm=now,
                to=utils.EOT
            )


class EnvironmentEntity(VersionedEntity):

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

    label = 'Host'
    state_label = 'HostState'
    identity_property = 'hostname'

    def __str__(self):
        return '{}'.format(getattr(self, 'hostname', None))


class VirtualenvEntity(VersionedEntity):

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

class PythonPackageEntity(VersionedEntity):

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
