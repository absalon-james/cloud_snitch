from django.test import TestCase

from api.diff import Node


class TestNode(TestCase):

    def test_dirty(self):
        """Test the node.dirty property."""
        n = Node('someid', 'somelabel')
        self.assertFalse(n.dirty)

        n.cleaned = True

        n.left_props = True
        self.assertTrue(n.dirty)

        n.left_props = False
        n.right_props = True
        self.assertTrue(n.dirty)

        n.right_props = False
        n.rel_changed = True
        self.assertTrue(n.dirty)

    def test_cleaned_props(self):
        """Test that samevalue properties are moved to both props."""
        n = Node('someid', 'somelabel')
        self.assertFalse(n.cleaned)

        n.left_props = {
            'leftprop': 'leftval',
            'bothprop': 'bothval',
            'diffprop': 'diffval1'
        }

        n.right_props = {
            'rightprop': 'rightval',
            'bothprop': 'bothval',
            'diffprop': 'diffval2'
        }

        n.clean()
        self.assertTrue(n.cleaned)
        self.assertDictEqual(n.left_props, {
            'leftprop': 'leftval',
            'diffprop': 'diffval1'
        })
        self.assertDictEqual(n.right_props, {
            'rightprop': 'rightval',
            'diffprop': 'diffval2'
        })
        self.assertDictEqual(n.both_props, {
            'bothprop': 'bothval'
        })

    def test_cleaned_descendents(self):
        """Test that rel_changed is marked."""
        n = Node('someid', 'somelabel')
        self.assertFalse(n.rel_changed)

        # Test left descendent
        n.children = {'childmodel': {'theid': {'side': 'left'}}}
        n.clean()
        self.assertTrue(n.rel_changed)

        # Test right descendent
        n.cleaned = False
        n.rel_changed = False
        n.children = {'childmodel': {'theid': {'side': 'right'}}}
        n.clean()
        self.assertTrue(n.rel_changed)

        # Test descendent on both sides
        n.cleaned = False
        n.rel_changed = False
        n.children = {'childmodel': {'theid': {'side': 'both'}}}
        n.clean()
        self.assertFalse(n.rel_changed)

    def test_add_property_left(self):
        """Test adding property from the left."""
        n = Node('someid', 'somelabel')
        n.add_property('prop', 'val', 'left')
        self.assertDictEqual(n.left_props, {'prop': 'val'})

    def test_add_property_right(self):
        """Test adding property from the right."""
        n = Node('someid', 'somelabel')
        n.add_property('prop', 'val', 'right')
        self.assertDictEqual(n.right_props, {'prop': 'val'})

    def test_update_left(self):
        """Test updating from the left."""
        n = Node('someid', 'somelabel')
        d = {'prop1': 'val1', 'prop2': 'val2'}
        n.update(d, 'left')
        self.assertDictEqual(d, n.left_props)

    def test_update_right(self):
        """Test updating from the right."""
        n = Node('someid', 'somelabel')
        d = {'prop1': 'val1', 'prop2': 'val2'}
        n.update(d, 'right')
        self.assertDictEqual(d, n.right_props)
