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

    def __init__(self, **kwargs):
        """Init the versioned entity instance.

        This sets attributes according to property lists.
        """
        props = (self.state_properties + self.static_properties)
        props.append(self.identity_property)
        for prop in props:
            setattr(self, prop, kwargs.get(prop))

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
        return cls(**({k: v for k,v in record.items()}))

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
        else:
            logger.debug('Data is not dirty')

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

    def update(self, session):
        with session.begin_transaction() as tx:
            exists = self.find(tx, self.identity)
            if exists is None:
                logger.debug("{} does not exist. creating ...".format(self.label))
                record = self.create(tx)
            else:
                self._update_state(tx)


class HostEntity(VersionedEntity):

    label = 'Host'
    state_label = 'HostState'
    identity_property = 'hostname'
    static_properties = ['created_at']
    state_properties = ['num_cores']

    def __str__(self):
        return '{} - {} - {} cores'.format(
            getattr(self, 'hostname', None),
            getattr(self, 'created_at', None),
            getattr(self, 'num_cores', None)
        )
