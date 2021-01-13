from config import PAYLOAD_DELIMITER
from election.ElectionMessage import ElectionMessage

class ElectionProtocol:
    LCR_ELECTION_MESSAGE = "{id}:{is_leader}"

def from_election_message(election_message: ElectionMessage):
    return ElectionProtocol.LCR_ELECTION_MESSAGE.format(id=election_message.participant_id, is_leader=election_message.is_leader)


def to_election_message(data: str):
    chunks = data.split(PAYLOAD_DELIMITER)
    return ElectionMessage(participant_id=chunks[0], is_leader=chunks[1])
