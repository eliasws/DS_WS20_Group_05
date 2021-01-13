from unittest import TestCase

from models.Host import Host
from models.Ring import Ring


class TestRing(TestCase):

    def test_ordering(self):
        own_node = Host("0000000", 0000)
        node_one = Host("1111111", 1111)
        node_two = Host("2222222", 2222)
        ring = Ring(own_node)

        ring.add_node(node_one)
        ring.add_node(node_two)

        assert ring.nodes[0].id == own_node.id
        assert ring.nodes[1].id == node_one.id
        assert ring.nodes[2].id == node_two.id


    def test_multiple_add(self):
        own_node = Host("0000000", 0000)
        node_one = Host("1111111", 1111)
        node_two = Host("2222222", 2222)
        ring = Ring(own_node)

        ring.add_node(node_one)
        ring.add_node(node_two)
        ring.add_node(node_two)
        ring.add_node(node_two)
        ring.add_node(node_two)

        assert len(ring.nodes) == 3

    def test_ordering_wrong(self):
        own_node = Host("0000000", 0000)
        node_one = Host("1111111", 1111)
        node_two = Host("2222222", 2222)
        ring = Ring(own_node)

        ring.add_node(node_two)
        ring.add_node(node_one)

        assert ring.nodes[0].id == own_node.id
        assert ring.nodes[1].id == node_one.id
        assert ring.nodes[2].id == node_two.id

    def test_ordering_delete(self):
        own_node = Host("0000000", 0000)
        node_one = Host("1111111", 1111)
        node_two = Host("2222222", 2222)
        ring = Ring(own_node)

        ring.add_node(node_one)
        ring.remove_node(node_one)
        ring.add_node(node_two)

        assert len(ring.nodes) == 2
        assert ring.nodes[0].id == own_node.id
        assert ring.nodes[1].id == node_two.id


    def test_get_right_neighbour(self):
        own_node = Host("0000000", 0000)
        node_one = Host("1111111", 1111)
        node_two = Host("2222222", 2222)
        ring = Ring(own_node)

        ring.add_node(node_one)
        ring.remove_node(node_one)
        ring.add_node(node_two)

        neighbour = ring.get_right_neighbour()

        assert neighbour.id == node_two.id
