class ElectionMessage:
    def __init__(self, participant_id, is_leader):
        self.is_leader = is_leader
        self.participant_id = participant_id
