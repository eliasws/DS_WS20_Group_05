from config import PAYLOAD_DELIMITER
from dynamic_discovery.BroadcastMessage import BroadcastMessage


# class BroadcastProtocol:
#     DISCOVERY_MESSAGE_SERVER = "BC:S"
#     DISCOVERY_MESSAGE_CLIENT = "BC:C"


def from_broadcast_message(broadcast_message: BroadcastMessage):
    return PAYLOAD_DELIMITER.join([str(broadcast_message.port)])


def to_broadcast_message(data: str):
    return BroadcastMessage(data)
