import json
import uuid

from config import BUFFER_SIZE, UNICAST_PORT, PAYLOAD_DELIMITER, DEBUG
from game.models.Game import Game
from models.Host import Host, HostType
from models.Ring import Ring
from models.SeverGroup import KnownHostGroup
from services.DiscoveryService import DiscoveryService
from services.HeartbeatService import HeartbeatService
from services.SocketService import SocketService
from util.KeyboardInput import KeyboardThread
from util.address_helper import get_local_address, get_random_unicast_port
from util.terminal_helper import cls

server_address = get_local_address()  # '127.0.0.1'  #
server_port = UNICAST_PORT  # 10001
client_port = get_random_unicast_port()  # 10001
client_address = get_local_address()  # 10001
buffer_size = BUFFER_SIZE  # 4096
client_id = uuid.uuid1()


class Client:

    def __init__(self):
        self.own_host = Host(
            str(uuid.uuid1()),
            get_local_address(),
            get_random_unicast_port(),
            HostType.CLIENT
        )

        self.current_game = None
        self.currently_initializing = []
        self.leader = None

        print(f'############################################ \n'
              f'# CLIENT                                     \n'
              f'# Id: {self.own_host.id} #\n'
              f'# Address: {self.own_host.address}:{self.own_host.unicast_port}       #\n'
              f'############################################ \n')

        self.ring = Ring(self.own_host)
        self.server_ring = Ring(self.own_host)

        self.socket_service = SocketService(self.own_host, self.on_host_failed)
        self.socket_service.sockets.remove(self.socket_service.broadcast_socket)
        self.all_host_group = KnownHostGroup(self.own_host, self.ring, self.server_ring, self.socket_service)
        self.all_host_group.add_participant(self.own_host)

        self.socket_service.set_on_broadcast_delivered(self.on_broadcast_received)
        self.socket_service.set_on_multicast_delivered(self.on_server_multicast_received)
        self.socket_service.set_on_unicast_delivered(self.on_unicast_received)

        self.discovery_service = DiscoveryService(self.own_host, self.socket_service, None)

        self.heartbeat_service = HeartbeatService(self.own_host, self.ring, self.socket_service)
        self.heartbeat_service.set_on_heartbeat_missing(self.on_host_missing)
        self.keybord = KeyboardThread(self.take_input)

        self.discovery_service.daemon = True
        self.keybord.daemon = True
        self.socket_service.daemon = True

        self.discovery_service.start_broadcasting()
        self.heartbeat_service.start_heartbeat()

        self.socket_service.start()
        self.discovery_service.start()
        self.keybord.start()

        self.keybord.join(1)
        self.socket_service.join(1)
        self.discovery_service.join(1)

    def on_broadcast_received(self, host: Host, method: str, message: str):
        pass

    def on_unicast_received(self, host: Host, method: str, message: str):
        if method == "SERVER/WELCOME":
            print("Got other host, stop broadcasting")
            self.discovery_service.stop_broadcasting()
            data = json.loads(message)
            hosts = json.loads(data.get("hosts"))
            list_of_hosts = [Host.from_json(h) for h in hosts]
            for new_host in list_of_hosts:
                self.currently_initializing.append(new_host.id)
                self.socket_service.send_unicast(new_host, "SERVER/JOIN", "")
        elif method == "SERVER/JOINED":
            print("Got answer from host!")
            self.all_host_group.add_participant(host)
            self.currently_initializing.remove(host.id)
            if message == "True":
                print("Got leader")
                self.leader = host
            if len(self.currently_initializing) == 0:
                print("Announce new group")
                self.socket_service.add_group(self.all_host_group)
                self.all_host_group.announce_participants()
                self.run_game()
        if method == "SERVER/JOIN":
            self.all_host_group.add_participant(host)
            print("ANSWERED HOST!")
            current_leader = False
            self.socket_service.send_unicast(host, "SERVER/JOINED", str(current_leader))
        elif method == "GS/MS":
            print(message)
        elif method == "GS/ERROR":
            self.run_game()
            print(message)
        elif method == "GS/LS":
            self.run_game()
            print(message)
        elif method == "HB":
            self.heartbeat_service.on_heartbeat_received(host, message)

    def on_host_failed(self):
        self.all_host_group.remove_participant(self.all_host_group.ring.get_right_neighbour())
        self.all_host_group.announce_participants()

    def on_server_multicast_received(self, host: Host, method: str, message, header):
        self.all_host_group.on_multicast_received(host, method, message, header)
        if method == "LCR/LEADER_CHANGED":
            message_chunks = message.split(PAYLOAD_DELIMITER)
            new_leader_id = message_chunks[0]
            print("Leader changed to ", new_leader_id)
            new_leader = self.all_host_group.get_host(new_leader_id)
            if not new_leader:
                print("We dont know about new leader, abort")
            self.leader = new_leader
            self.run_game()
        if method == "GS/OV":
            game = Game.from_pickle(message)
            if game.get_player(self.own_host.id):
                print("SET GAME")
                self.current_game = game
            elif self.current_game and game.id == self.current_game.id:
                self.current_game = None
            self.run_game()
        elif method == "GS/WIN":
            base_message = json.loads(message)
            game_id = base_message.get('game_id')
            if self.current_game and game_id == self.current_game.id:
                print(base_message.get('message'))
            self.run_game()

    def take_input(self, input):
        self.socket_service.send_unicast(self.leader, "GS", input)

    def run_game(self):
        # if not DEBUG:
        #    cls()
        if self.current_game:
            self.current_game.draw()
        print("Type in direction (create:game_name ,display, join:gamename:name, leave, up, down, left, right) :")

    def on_host_missing(self, host: Host):
        print(f"HOST {host.id} NOT ANSWERING!")
        self.all_host_group.remove_participant(host)
        self.all_host_group.announce_participants()


if __name__ == "__main__":
    client = None
try:
    client = Client()
except KeyboardInterrupt:
    print("Shut down because keyboard interrupted")
    raise
