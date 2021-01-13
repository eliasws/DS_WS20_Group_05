import json


class HostType:
    SERVER = "server"
    CLIENT = "client"


class Host(object):

    def __init__(self, id: str, address: str, unicast_port: int, host_type: HostType = HostType.SERVER):
        self.id = id
        self.address = address
        self.unicast_port = unicast_port
        self.host_type = host_type
        self.message_history = {}
        self.message_seq = 0
        self.last_message_seq = 0
        self.open_ack = False

    def to_json(self):
        test = {
           "id": self.id,
           "address": self.address,
           "unicast_port": self.unicast_port,
           "host_type": self.host_type,
        }
        return json.dumps(test, default=lambda o: o.__dict__)

    @staticmethod
    def from_json(data: str):
        return json.loads(data, object_hook=lambda o: Host(**o))

    def __eq__(self, other):
        return self.id == other.id
