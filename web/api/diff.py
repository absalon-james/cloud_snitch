import logging

from cloud_snitch.models import registry
from .query import Query

logger = logging.getLogger(__name__)

LEFT = 'left'
RIGHT = 'right'
BOTH = 'both'


class Node:
    """Model a node in a graph of the differences."""

    def __init__(self, identity, model):
        """Init the node.

        :param identity: Identity of the node
        :type identity: str
        :param model: Type|Label of the node
        :type model: str
        """
        self.model = model
        self.identity = identity
        self.parents = set()
        self.left_props = {}
        self.both_props = {}
        self.right_props = {}
        self.children = {}
        self.changed = False
        self.cleaned = False
        self.rel_changed = False

    @property
    def dirty(self):
        """Determine if this node's properties are dirty.

        :returns: True for dirty, False otherwise
        :rtype: bool
        """
        self.clean()
        return self.left_props or self.right_props or self.rel_changed

    def update(self, d, side):
        """Update properties by d

        :param d: Key value map of properties.
        :type d: dict
        :param side: Which side is d coming from(left|right)
        :type side: str
        """
        for key, value in d.items():
            self.add_property(key, value, side)

    def clean(self):
        """Collect properties that are the same on both."""
        # Dont clean if already cleaned.
        if self.cleaned:
            return

        # Start a list of properties that can be moved.
        toremove = []
        for key, value in self.left_props.items():
            if value == self.right_props.get(key):
                toremove.append(key)
                self.both_props[key] = value

        # Remove properties from both sides
        for i in toremove:
            del self.left_props[i]
            del self.right_props[i]

        # Check relationships:
        for model, modeldict in self.children.items():
            for identity, reldict in modeldict.items():
                if reldict['side'] != 'both':
                    self.rel_changed = True

        # Mark as cleaned.
        self.cleaned = True

    def add_property(self, key, value, side):
        """Add property to the node.

        :param key: Key|Name of the property
        :type key: str
        :param value: str
        :type value: str
        :param side: Which side is the property coming from.
        :type side: str
        """
        if side == LEFT:
            this = self.left_props
        else:
            this = self.right_props
        this[key] = value

    def add_child(self, model, node, side):
        """Add child to the node.

        :param model: Type|Label of the child node.
        :type model: str
        :param node: Node to add
        :type node: Node
        :param side: Which side is the node coming from?
        :type side: str
        """
        model_rel = self.children.setdefault(model, {})
        node_rel = model_rel.setdefault(node.identity, {
            'side': side,
            'node': node
        })
        if side != node_rel['side']:
            node_rel['side'] = BOTH

    def remove_child(self, model, identity):
        """Remove a child.

        :param model: Type|Label of the node to remove
        :type model: str
        :param identity: Identity of the node
        :type identity: str
        """
        if model in self.children:
            if identity in self.children[model]:
                if self.children[model][identity]['side'] == 'both':
                    del self.children[model][identity]
                    return True
        return False

    def todict(self):
        """Dictionary representation of the node.

        :param rel_side: Which side does the node belong to
        :type rel_side: str
        :returns: Dict representation of node
        :rtype: dict
        """
        d = {
            'model': self.model,
            'left': self.left_props,
            'both': self.both_props,
            'right': self.right_props,
        }
        return d

    def toframe(self, rel_side=None):
        """Create structural representation of the node.

        :param rel_side: Which side of the diff is the node on?
        :type rel_side: string
        :returns: Dict representation of structure.
        :rtype: dict
        """
        children = []
        d = {
            'side': rel_side,
            'model': self.model,
            'id': self.identity,
            'children': children
        }
        for model, modeldict in self.children.items():
            for identity, nodedict in modeldict.items():
                children.append(nodedict['node'].toframe(nodedict['side']))
        return d


class DiffResult:
    """Convenience class for interfacing with a diffdict."""
    def __init__(self, diffdict):
        """Init the DiffResult

        :param diffdict: Dict representation of diff
        :type diffdict: dict
        """
        self.diffdict = diffdict

    def getnodes(self, offset, limit):
        """Get up to limit nodes starting at offset.

        :param offset: Where to start
        :type offset: int
        :param limit: Maximum number of nodes to retrieve
        :type limit: int
        """
        return self.diffdict['nodes'][offset:(offset + limit)]

    def getnode(self, model, identity):
        """Get a specific node identified by model and id.

        :param model: Name of the model
        :type model: str
        :param identity: Id of an object
        :type identity: str
        :returns: Dict representation of node or None
        :rtype: dict|None
        """
        index = self.diffdict['nodemap'].get(model, {}).get(identity)
        if index is not None:
            return self.diffdict['nodes'][index]
        return None

    def frame(self):
        """Get the frame of the diff

        :returns: Dict representation of structure or frame
        :rtype: dict
        """
        return self.diffdict['frame']


class Diff:
    """Models a graph that is a diff of two objects."""

    pagesize = 1000

    def __init__(self, model, identity, left_time, right_time):
        """Init the diff

        :param model: Type|Label of the root node
        :type model: str
        :param identity: Identity of the root node
        :type identity: str
        :param left_time: First timestamp in milliseconds
        :type left_time: int
        :param right_time: Second timestamp in milliseconds
        :type right_time: int
        """
        self.nodes = {}
        self.model = model
        self.identity = identity
        self.left_time = left_time
        self.right_time = right_time

        # Feed data from the left
        self.feedleft()

        # Feed data from the right
        self.feedright()

        # Move unchanged properties to both
        self.clean()

        # Remove unchanged nodes with unchanged children.
        self.prune()

    def getnode(self, model, data):
        """Get a node of model type matching data.

        Create a new node if one does not exist.

        :param model: Name of the model
        :type model: str
        :param data: Dict representation of node
        :type data: dict
        :returns: Node with matching data
        :rtype: Node
        """
        identity = data[registry.identity_property(model)]
        nodemap = self.nodes.setdefault(model, {})
        node = nodemap.setdefault(identity, Node(identity, model))
        return node

    def feedpath(self, path, time, side):
        """Feed all of a path from a side to the diff.

        :param path: List of models indicating path through data to a model
        :type path: list
        :param time: Integer milliseconds since epoch
        :type time: int
        :param side: Which side to feed the diff from.
        :type side: str
        """
        # Build query
        q = Query(path[-1]) \
            .filter(
                registry.identity_property(self.model),
                '=',
                self.identity, self.model
            ).time(time)

        # Start at page 1 and page through all results.
        page = 1
        records = q.page(page, self.pagesize)
        while (records):
            for record in records:
                parent = None
                for label in path:
                    # Update diff with results
                    node = self.getnode(label, record[label])
                    node.update(record[label], side)

                    # Make parent -> child relationship
                    if parent is not None:
                        parent.add_child(label, node, side)
                        node.parents.add(parent)

                    # Advance parent for next part of path.
                    parent = node

            page += 1
            records = q.page(page, self.pagesize)

    def feed(self, time, side):
        """Feed all paths from a side to the diff.

        :param time: Integer milliseconds since epoch
        :type side: Which side to feed from
        """
        # Iterarate over every path.
        paths = registry.forest.paths_from(self.model)
        for p in paths:
            self.feedpath(p, time, side)

    def feedleft(self):
        """Feed data from the left side."""
        self.feed(self.left_time, LEFT)

    def feedright(self):
        """Feed data from the right side."""
        self.feed(self.right_time, RIGHT)

    def clean(self):
        """Mark nodes that have changed as changed.

        Mark all ancestors of changed nodes as changed.
        """
        # Iterate over the model -> nodes dictionary
        for model, nodedict in self.nodes.items():
            # Iterate over the identity -> node dictionary
            for identity, node in nodedict.items():
                # If node is dirty, mark entire path as changed
                if node.dirty:
                    stack = [node]
                    while stack:
                        current = stack.pop()
                        # If already changed, no need to continue.
                        if current.changed:
                            continue
                        current.changed = True
                        for parent in current.parents:
                            stack.append(parent)

    def prune(self):
        """Remove unchanged nodes that also have unchanged children."""
        for model, nodedict in self.nodes.items():
            toremove = []
            # Remove unchanged children from parents
            for identity, node in nodedict.items():
                if not node.changed:
                    # Add to remove list if removed from every parent
                    removed = [
                        p.remove_child(model, identity)
                        for p in node.parents
                    ]
                    if all(removed):
                        toremove.append(identity)
            # Remove unchanged nodes from datasructure
            for key in toremove:
                del nodedict[key]

    def result(self):
        """Create diff result that can be cached/chunked.

        :returns: Result of the diff
        :rtype: DiffResult
        """
        diffdict = {
            'frame': None,
            'nodes': [],
            'nodemap': {},
            'nodecount': 0
        }
        rootnodes = self.nodes[self.model]
        if rootnodes:
            diffdict['frame'] = next(iter(rootnodes.values())).toframe()
            index = 0
            for model, nodedict in self.nodes.items():
                modelmap = {}
                for identity, node in nodedict.items():
                    n = node.todict()
                    diffdict['nodes'].append(n)
                    modelmap[identity] = index
                    index += 1
                if modelmap:
                    diffdict['nodemap'][model] = modelmap

        diffdict['nodecount'] = len(diffdict['nodes'])
        return DiffResult(diffdict)
