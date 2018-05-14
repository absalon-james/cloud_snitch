import json
import logging
import pprint
from cloud_snitch import utils
from cloud_snitch.decorators import transient_retry
from cloud_snitch.exc import PropertyAlreadyExistsError

logger = logging.getLogger(__name__)


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

    def _update(self, tx, edges, time_in_ms):
        """Update the versioned edge set

        First match all edges from source to dest_type entities that
        are current(the `to` field is set to end of time).

        Determine the edges that are no longer current and mark them with
        a `to` set to the run completion time

        Create the edges that need to be added.

        :param tx: neo4j transaction context
        :type tx: neo4j.v1.api.Transaction
        :param edges: List of entity objects to maintain relationships to
        :type edges: list
        :param time_in_ms: Time in milliseconds.
        :type time_in_ms: int
        """
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
                to=time_in_ms
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
                frm=time_in_ms,
                to=utils.EOT
            )

    @transient_retry
    def update(self, session, edges, time_in_ms):
        """Update edges inside of a transaction.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param edges: List of entity instances to maintain edges
        :type edges: list
        :param time_in_ms: Time in milliseconds
        :type time_in_ms: int
        """
        with session.begin_transaction() as tx:
            self._update(tx, edges, time_in_ms)


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

    # Children - Relationships to other entities from this entity
    children = {}

    def __init__(self, **kwargs):
        """Init the versioned entity instance.

        This sets attributes according to property lists.
        """
        prop_set = set()

        # Set up properties
        props = (self.state_properties + self.static_properties)
        props.append(self.identity_property)
        for prop in props:
            if prop in prop_set:
                raise PropertyAlreadyExistsError(self.label, prop)
            setattr(self, prop, self._encode(kwargs.get(prop)))
            prop_set.add(prop)

        # Compute values for keys that are concatenated
        for prop, cat_list in self.concat_properties.items():
            if not kwargs.get(prop):
                val = '-'.join(
                    [str(self._encode(kwargs.get(p)))for p in cat_list]
                )
                setattr(self, prop, val)

        # Set up relationships
        for prop, rtuple in self.children.items():
            rel_name, rel_type = rtuple
            if prop in prop_set:
                raise PropertyAlreadyExistsError(self.label, prop)
            edges = VersionedEdgeSet(rel_name, self, rel_type)
            setattr(self, prop, edges)
            prop_set.add(prop)

    def _encode(self, value):
        """Encodes property into a primitive type suitable for neo4j.

        Looks for lists and dicts. Converts to json

        :param value: Value to encode
        :type value: object
        :returns: Encoded object
        :rtype: object
        """
        if isinstance(value, dict) or isinstance(value, list):
            value = json.dumps(value, sort_keys=True)
        return value

    @property
    def identity(self):
        """Get value of identity property.

        :returns: Value of the identity property
        :rtype: str
        """
        return getattr(self, self.identity_property, None)

    @classmethod
    def find(cls, session, identity):
        """Finds an entity by identity.

        :param session: neo4j driver session
        :type session: neo4j.v1.session.BoltSession
        :param identity: Identity to find
        :type identity: str
        :returns: Instance of version entity or None
        :rtype: VersionedEntity|None
        """
        with session.begin_transaction() as tx:
            return cls.find_transaction(tx, identity)

    @classmethod
    def find_transaction(cls, tx, identity):
        """Finds an entity using provided transaction.

        :param tx: neo4j transaction context.
        :type tx: neo4j.v1.api.Transaction
        :param identity: Identity to find
        :type identity: str
        :returns: Instance of versioned entity
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

        # Check for empty result
        if record is None:
            return record

        # Build and return entity
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

    def _update_state(self, tx, time_in_ms):
        """Close current state and create a new state if data differs.

        :param tx: neo4j transaction context.
        :type tx: neo4j.v1.api.Transaction
        :param time_in_ms: Time in milliseconds
        :type time_in_ms: int
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

            # Mark current state as old
            cypher = """
                MATCH (c:{} {{ {}:$identity }})
                   -[r1:HAS_STATE {{to: $EOT}}]
                   ->(currentState:{})
                SET r1.to = $completed
            """
            cypher = cypher.format(
                self.label,
                self.identity_property,
                self.state_label
            )
            tx.run(
                cypher,
                identity=self.identity,
                completed=time_in_ms,
                EOT=utils.EOT
            )

            # Create relationship
            prop_map.update({
                'EOT': utils.EOT,
                'completed': time_in_ms,
                'identity': self.identity
            })
            cyper = """
                MATCH (s:{} {{ {}:$identity }})
                CREATE (s)
                    -[r2:HAS_STATE {{to: $EOT, from: $completed }}]
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

    def _update(self, tx, time_in_ms):
        """Update the entity in the graph.

        :param tx: neo4j transaction context
        :type tx: neo4j.v1.api.Transaction
        :param tx: Time in milliseconds
        :type tx: int
        """
        static_props = {}
        for prop in self.static_properties:
            val = getattr(self, prop, None)
            if val is not None:
                static_props[prop] = val

        parts, prop_map = self._props_set_clause('n', self.static_properties)

        if prop_map:
            create_clause = (
                'ON CREATE SET  n.created_at = $completed, {}'.format(parts)
            )
            update_clause = 'ON MATCH SET {}'.format(parts)
        else:
            create_clause = 'ON CREATE SET  n.created_at = $completed'
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
        logger.debug("Updating identity:\n{}".format(cypher))
        tx.run(
            cypher,
            completed=time_in_ms,
            identity=self.identity,
            **prop_map
        )
        self._update_state(tx, time_in_ms)

    @transient_retry
    def update(self, session, time_in_ms):
        """Update the entity in the graph.

        Creates the transaction context for the update

        :param session: Neo4j driver session.
        :type session: neo4j.v1.session.BoltSession
        :param time_in_ms: Time in milliseconds
        :type time_in_ms: int
        """
        with session.begin_transaction() as tx:
            self._update(tx, time_in_ms)

    @classmethod
    def todict(cls, children=False):
        d = dict(
            label=cls.label,
            state_label=cls.state_label,
            identity_property=cls.identity_property,
            static_properties=cls.static_properties,
            state_properties=cls.state_properties
        )
        if d:
            children = {}
            for rel_name, childklass in cls.children.values():
                children[rel_name] = childklass.todict(children=children)
            d['children'] = children
        return d
