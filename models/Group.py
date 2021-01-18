import json
from typing import List

from models.Host import Host
from models.Sequencer import Sequencer
from services.SocketService import SocketService


class Group:
    def __init__(self, identifier, socket_service: SocketService):
        self.sequencer = Sequencer()
        self.identifier = identifier
        self.socket_service = socket_service
        self.participants = []

        self.group_last_message_delivered_seq = None
        self.hold_back_queue = []
        self.message_history = {}
        self.suggested_sequence_number = 0

        #New
        self.rel_seq = 0  # S
        self.rel_delivered_seq = {}  # R
        # TODO: remove?
        self.rel_hold_back_queue = {}
        self.rel_message_history = {}
        self.group_sent_messages = {}

    def on_multicast_received(self, host, method: str, message, header):
        if method == "MAIN_GROUP/HOSTS":
            if 'resent' not in header:
                hosts = json.loads(message)
                list_of_hosts = [Host.from_json(h) for h in hosts]
                self.set_host_list(list_of_hosts)
        if method == "MAIN_GROUP/GET_HOSTS":
            self.socket_service.send_group_multicast(
                self,
                f"MAIN_GROUP/HOSTS",
                json.dumps([ob.to_json() for ob in self.participants]),
            )

    def set_host_list(self, hosts: List[Host]):
        self.participants = hosts

    def announce_participants(self):
        self.socket_service.send_group_multicast(
            self,
            f"MAIN_GROUP/HOSTS",
            json.dumps([ob.to_json() for ob in self.participants])
        )

    def add_participant(self, host: Host):
        if host not in self.participants:
            self.participants.append(host)
        else:
            print("[Group]: Tried to add existing participant")

    def get_host(self, participant_id):
        return next((participant for participant in self.participants if participant.id == participant_id), None)

    def remove_participant(self, host: Host):
        if host in self.participants:
            self.participants.remove(host)
        else:
            print("[Group]: Cannot remove participant, as its non-existent")
