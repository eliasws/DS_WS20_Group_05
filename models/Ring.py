from typing import List

from models.Host import Host


class Ring:
    def __init__(self, own_node: Host):
        self.own_node = own_node
        self.nodes = []

    def get_node(self, id):
        if id in [node.id for node in self.nodes]:
            return next((node for node in self.nodes if node.id == id), None)
        else:
            print("[Ring] Cannot find node")

    def add_node(self, node: Host):
        if node not in self.nodes:
            self.nodes.append(node)
            self._form_ring()
        else:
            print("[Ring]: Tried to add existing node")

    def set_nodes(self, nodes: List[Host]):
        self.nodes = nodes

    def remove_node(self, node: Host):
        if node in self.nodes:
            self.nodes.remove(node)
            self._form_ring()
        else:
            print("[Ring]: Cannot remove node, as its non-existent")

    def get_right_neighbour(self):
        return self._get_neighbour(reverse=True)

    def get_left_neighbour(self):
        return self._get_neighbour()

    def _form_ring(self):
        self.nodes = sorted(self.nodes, key=_get_id)

    def _get_neighbour(self, reverse=False):
        if self.own_node not in self.nodes:
            return self.own_node
        pos = self.nodes.index(self.own_node)

        if len(self.nodes) == 1:
            return self.own_node

        if reverse:
            if pos == 0:
                return self.nodes[len(self.nodes) - 1]
            else:
                return self.nodes[pos - 1]
        else:
            if pos + 1 == len(self.nodes):
                return self.nodes[0]
            else:
                return self.nodes[pos + 1]


def _get_id(node: Host):
    return node.id
