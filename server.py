import time
import uuid
import json

from models.Ring import Ring
from models.SeverGroup import KnownHostGroup
from services.DiscoveryService import DiscoveryService
from services.GameService import GameService
from services.HeartbeatService import HeartbeatService
from services.SocketService import SocketService
from config import MAX_BROADCAST_RETRIES
from election.LCRElection import LCRElection
from models.Host import Host, HostType
from util.address_helper import get_local_address, get_random_unicast_port


class Server:
    def __init__(self):
        self.own_host = Host(str(uuid.uuid1()), get_local_address(), get_random_unicast_port(), HostType.SERVER)

        print(f'############################################ \n'
              f'# SERVER                                     \n'
              f'# Id: {self.own_host.id} #\n'
              f'# Address: {self.own_host.address}:{self.own_host.unicast_port}       #\n'
              f'############################################ \n')

        self.socket_service = SocketService(self.own_host, self.on_host_failed)
        self.socket_service.set_on_broadcast_delivered(self.on_broadcast_received)
        self.socket_service.set_on_multicast_delivered(self.on_server_multicast_received)
        self.socket_service.set_on_unicast_delivered(self.on_unicast_received)

        self.currently_initializing = []
        self.in_init = False
        self.ring = Ring(self.own_host)
        self.server_ring = Ring(self.own_host)

        self.all_host_group = KnownHostGroup(self.own_host, self.ring, self.server_ring, self.socket_service)
        self.all_host_group.add_participant(self.own_host)

        self.election_service = LCRElection(self.socket_service, self.own_host, self.server_ring, self.all_host_group)

        self.discovery_service = DiscoveryService(self.own_host, self.socket_service, self.discovery_counter)

        self.game_service = GameService(self.socket_service, self.all_host_group)

        self.heartbeat_service = HeartbeatService(self.own_host, self.ring, self.socket_service)
        self.heartbeat_service.set_on_heartbeat_missing(self.on_host_missing)

        self.discovery_service.daemon = True
        self.socket_service.daemon = True
        self.heartbeat_service.daemon = True

        self.discovery_service.start_broadcasting()
        self.heartbeat_service.start_heartbeat()

        self.socket_service.start()
        self.discovery_service.start()

        self.socket_service.join()
        self.discovery_service.join()

    def discovery_counter(self, counter):
        if counter > MAX_BROADCAST_RETRIES:
            self.discovery_service.stop_broadcasting()
            self.election_service.start_election()
            self.socket_service.add_group(self.all_host_group)
            self.all_host_group.announce_participants()

    def on_broadcast_received(self, host: Host, method: str, message: str):
        if self.in_init:
            return

        current_leader = self.election_service.current_leader

        if host.host_type == HostType.CLIENT and not current_leader:
            print("No leader elected yet, ignore client request")
            return

        print("Got other SERVER, stop broadcasting")
        self.discovery_service.stop_broadcasting()

        contact_host = self.own_host

        # If we currently have no leader we send the own address
        # as contact-address
        if current_leader:
            contact_host = current_leader

        self.socket_service.add_group(self.all_host_group)

        self.socket_service.send_unicast(
            host,
            "SERVER/WELCOME",
            json.dumps({
                "host": contact_host.to_json(),
                "hosts": self.all_host_group.to_json(),
            })
        )
        self.in_init = False

    def on_unicast_received(self, host: Host, method: str, message: str):
        if method == "SERVER/WELCOME":
            print("Got other host, stop broadcasting")
            self.discovery_service.stop_broadcasting()
            data = json.loads(message)
            host = Host.from_json(data.get("host"))
            hosts = json.loads(data.get("hosts"))
            list_of_hosts = [Host.from_json(h) for h in hosts]
            for new_host in list_of_hosts:
                self.currently_initializing.append(new_host.id)
                self.socket_service.send_unicast(new_host, "SERVER/JOIN", "")
        if method == "SERVER/JOIN":
            self.all_host_group.add_participant(host)
            print("ANSWERED HOST!")
            current_leader = False
            if self.election_service.current_leader:
                current_leader = self.election_service.current_leader == self.own_host
            self.socket_service.send_unicast(host, "SERVER/JOINED", str(current_leader))
        if method == "SERVER/JOINED":
            print("Got answer from host!")
            self.all_host_group.add_participant(host)
            self.currently_initializing.remove(host.id)
            if message == "True":
                print("Got leader")
                self.election_service.set_leader(host.id)

            if len(self.currently_initializing) == 0:
                self.socket_service.add_group(self.all_host_group)

                self.all_host_group.announce_participants()

                self.socket_service.send_unicast(self.election_service.current_leader, "GS/SYNC_GAMES", '')

                time.sleep(3)
                if not self.election_service.leader_elected():
                    self.election_service.start_election()

        elif method == "HB":
            self.heartbeat_service.on_heartbeat_received(host, message)
        self.election_service.on_message_received(host, method, message)
        self.game_service.on_unicast_received(host, method, message)

    def on_server_multicast_received(self, host: Host, method: str, message: str, header):

        self.all_host_group.on_multicast_received(host, method, message, header)
        self.election_service.on_message_received(host, method, message)
        if method == "MAIN_GROUP/HOSTS":
            hosts = json.loads(message)
            list_of_hosts_id = [Host.from_json(h).id for h in hosts]
            if self.election_service.current_leader and self.election_service.current_leader.id not in list_of_hosts_id:
                self.election_service.start_election()
            elif not self.election_service.current_leader:
                self.election_service.start_election()
        self.game_service.on_multicast_received(host, method, message)

    def on_host_failed(self):
        self.all_host_group.remove_participant(self.all_host_group.ring.get_right_neighbour())
        self.all_host_group.announce_participants()

    def on_host_missing(self, host: Host):
        print(f"HOST {host.id} NOT ANSWERING!")
        self.all_host_group.remove_participant(host)
        self.all_host_group.announce_participants()
        if self.election_service.leader_elected() and host.id == self.election_service.get_leader().id:
            print("NOT ANSWERING HOST IS LEADER!")
            self.election_service.start_election()


if __name__ == "__main__":
    server = None
try:
    server = Server()
except KeyboardInterrupt:
    print("Shut down because keyboard interrupted")
