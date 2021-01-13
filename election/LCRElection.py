import time

from config import PAYLOAD_DELIMITER
from services.SocketService import SocketService
from election.ElectionMessage import ElectionMessage
from election.election_converter import from_election_message, to_election_message
from models.Ring import Ring
from models.Host import Host


class LCRElection:
    def __init__(self, socket_service: SocketService, own_node: Host, ring, all_host_group):
        self.socket_service: SocketService = socket_service
        self.all_host_group = all_host_group
        self.current_leader: Host = None
        self.on_leader_changed = None
        self.ring: Ring = ring
        self.own_host: Host = own_node
        self.is_participant: bool = False
        self.election_started = time.time()
        self.retry_counter = 0

    def start_election(self):
        if not self.is_participant:
            print("[Election] Start election")
            self.is_participant = True
            self.send_message(self.own_host.id, False)

    def on_message_received(self, host: Host, method, message: str):
        if method == "LCR/LEADER_CHANGED":
            message_chunks = message.split(PAYLOAD_DELIMITER)
            new_leader_id = message_chunks[0]
            if not self.current_leader:
                self.set_leader(new_leader_id)
            if self.current_leader and self.current_leader.id != new_leader_id:
                print("[Election] Leader conflict, elect new leader")
                self.start_election()
        if method == "LCR/LEADER_ELECTION":
            right_neighbour = self.ring.get_right_neighbour()
            if not right_neighbour or right_neighbour.id != host.id:
                print(f"[Election] ERROR! Got message from wrong neighbour!")
                return
            election_message = to_election_message(message)
            if election_message.is_leader:
                self.is_participant = False
                self.set_leader(election_message.participant_id)
                if election_message.participant_id != self.own_host.id:
                    self.send_message(election_message.participant_id, True)
                else:
                    print("######## Im the leader now! #######")
                    self.announce_leader()
            else:
                print("[Election] Start participation")
                if not self.is_participant and election_message.participant_id < self.own_host.id:
                    self.is_participant = True
                    self.send_message(self.own_host.id, False)
                elif election_message.participant_id > self.own_host.id:
                    self.is_participant = True
                    self.send_message(election_message.participant_id, False)

    def set_on_leader_changed(self, func):
        self.on_leader_changed = func

    def set_leader(self, leader_id: str):
        leader = self.ring.get_node(leader_id)
        if leader:
            print(f"[Election] Set {leader_id} as leader")
            self.current_leader = leader
        else:
            print(f"[Election] ERROR! Could not find leader!")

    def announce_leader(self):
        self.socket_service.send_group_multicast(
            self.all_host_group,
            f"LCR/LEADER_CHANGED",
            self.current_leader.id
        )

    def leader_elected(self):
        return not not self.current_leader

    def get_leader(self):
        return self.current_leader

    def send_message(self, participant_id, is_leader):
        neighbour = self.ring.get_left_neighbour()
        election_message = ElectionMessage(participant_id, is_leader)
        data = from_election_message(election_message)
        self.socket_service.send_unicast(neighbour, "LCR/LEADER_ELECTION", data)
