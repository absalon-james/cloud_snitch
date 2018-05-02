import logging

from pkg_resources import iter_entry_points

logger = logging.getLogger(__name__)

_REGISTRY = None


class Node:
    """Models node in a tree in a forest."""
    def __init__(self, model):
        """Init the node

        :param model: Entity to represent
        :type model: class
        """
        self.model = model
        self.parent = None
        self.parent_rel = None
        self.children = {}

    @property
    def label(self):
        """Get label of model

        :return: Model label
        :rtype: str
        """
        return self.model.label


class Forest:
    """Collection of model trees.

    The root of a tree is a model with no parents.
    Each node in each tree contains references to children
    and to a parent.
    """
    def __init__(self, models):
        """Init the forest

        :param models: Dictionary of models keyed by label
        :type models: dict
        """
        self.nodes = {}
        self.roots = []

        # Create nodes for models
        for model in models.values():
            self.nodes[model.label] = Node(model)

        # Create node mappings
        self.grow()

        # Find beginnings of trees
        self.find_roots()

    def grow(self):
        """Establish relationships."""
        for node in self.nodes.values():
            for relname, childmodel in node.model.children.values():
                self.nodes[childmodel.label].parent = node
                self.nodes[childmodel.label].parent_rel = relname
                node.children[relname] = self.nodes[childmodel.label]

    def find_roots(self):
        """Find roots of trees.

        Roots are nodes with no parents.
        """
        self.roots = []
        for node in self.nodes.values():
            if node.parent is None:
                self.roots.append(node)

    def path(self, label):
        """Find path of a model with label.

        :param label: Label of model
        :type label: str
        :returns: List of (parent model label, relationship name) tuples
        :rtype: list|None
        """
        target_node = self.nodes.get(label)
        if target_node is None:
            return None

        path = []
        current = target_node
        while current.parent is not None:
            path.append((current.parent, current.parent_rel))
            current = current.parent
        return [(n.label, r) for n, r in reversed(path)]

    def paths_from(self, label):
        """Find all paths from a model with label.

        :param label: Label of model
        :type label: str
        :returns: List of paths from label
        :rtype: list
        """
        visited = set()
        paths = []

        current_node = self.nodes.get(label)
        stack = [current_node]
        while (stack):
            current = stack[-1]
            visited.add(current)
            for rel_name, child_node in current.children.items():
                if child_node not in visited:
                    stack.append(child_node)
                    break
            else:
                if not current.children:
                    paths.append([n.label for n in stack])
                stack.pop()
        return paths


class Registry:
    """Model information about models."""
    def __init__(self):
        """Init the registry."""
        self.models = {}
        self.load_models()
        self.forest = Forest(self.models)

    def load_models(self):
        """Load installed models from entry points."""
        for ep in iter_entry_points(group='cloud_snitch_models'):
            try:
                self.models[ep.name] = ep.load()
            except Exception:
                logger.warn(
                    'Unable to load cloud snitch model {}'.format(ep.name)
                )

    def identity_property(self, model):
        """Return the identity property of a targeted model.

        :param model: Model name
        :type model: str
        :returns: Name of the model identity property or None
        :rtype: str|None
        """
        klass = self.models.get(model)
        if klass is None:
            return None
        return klass.identity_property

    def state_properties(self, model):
        """Return the state properties of a targeted model

        :param model: Model name
        :type model: str
        :returns: List of state properties or None
        :rtype: list|None
        """
        klass = self.models.get(model)
        if klass is None:
            return None
        return sorted(klass.state_properties)

    def static_properties(self, model):
        """Return the static properties of a model

        :param model: Model name
        :type model: str
        :returns: List of static properties or None
        :rtype: list|None
        """
        klass = self.models.get(model)
        if klass is None:
            return None
        return sorted(klass.static_properties)

    def children(self, model):
        """Return the children of a model

        :param model: Model name
        :type model: str
        :returns: List of children model names or None
        :rtype: list|None
        """
        klass = self.models.get(model)
        if klass is None:
            return None
        return list(klass.children.keys())

    def modeldict(self, model):
        """Return an json serializable dict describing the model.

        :param model: Name of the model
        :type model: str
        :returns: Dict describing model
        :rtype: dict|None
        """
        klass = self.models.get(model)
        if klass is None:
            return None

        children = {}
        for name, childtuple in klass.children.items():
            children[name] = {
                'rel_name': childtuple[0],
                'label': childtuple[1].label
            }
        return dict(
            label=klass.label,
            state_label=klass.label,
            identity=klass.identity_property,
            static_properties=klass.static_properties,
            state_properties=klass.state_properties,
            children=children
        )

    def modeldicts(self):
        """Get a list of all model dicts.

        :returns: List of model dicts
        :rtype: list
        """
        dicts = []
        for model in self.models.keys():
            dicts.append(self.modeldict(model))
        return sorted(dicts, key=lambda x: x.get('label'))

    def properties(self, model=None):
        """Gather list of properties for all models or a single model.

        :param model: Name of a targeted model
        :type model: str
        :returns: List of properties.
        :rtype: list
        """
        prop_set = set()

        if model is None:
            models = self.models.keys()
        else:
            models = [model]

        for model in models:
            klass = self.models.get(model)
            if klass is not None:
                prop_set.add(klass.identity_property)
                for prop in klass.static_properties:
                    prop_set.add(prop)
                for prop in klass.state_properties:
                    prop_set.add(prop)

        return sorted(list(prop_set))

    def path(self, label):
        """Get path of a label within forest.

        :param label: Model label
        :type label: str
        :returns: List of (label, relationship name) tuples
        :rtype: list|None
        """
        return self.forest.path(label)
