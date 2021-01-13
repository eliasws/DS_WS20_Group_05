import json
from typing import List

from models.Group import Group
from models.Host import Host, HostType
from models.Ring import Ring
from services.SocketService import SocketService


class KnownHostGroup(Group):
    def __init__(
            self,
            own_node: Host,
            ring,
            server_ring,
            socket_service: SocketService,
    ):
        super().__init__("MAIN_GROUP", socket_service)
        self.server_ring = server_ring
        self.own_node = own_node
        self.ring = ring

    def add_participant(self, host: Host):
        super(KnownHostGroup, self).add_participant(host)
        self.ring.add_node(host)
        if host.host_type == HostType.SERVER:
            self.server_ring.add_node(host)

    def remove_participant(self, host: Host):
        super(KnownHostGroup, self).remove_participant(host)
        self.ring.remove_node(host)
        if host.host_type == HostType.SERVER:
            self.server_ring.remove_node(host)

    def set_host_list(self, hosts: List[Host]):
        if self.own_node not in hosts:
            hosts.append(self.own_node)

        super(KnownHostGroup, self).set_host_list(hosts)
        servers = [host for host in hosts if host.host_type == HostType.SERVER]
        clients = [host for host in hosts if host.host_type == HostType.CLIENT]
        self.ring.set_nodes(hosts)
        self.server_ring.set_nodes(servers)

    def to_json(self):
        return json.dumps([ob.to_json() for ob in self.participants])
