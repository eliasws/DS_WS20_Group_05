class Sequencer:
    def __init__(self):
        self.sequence = 0

    def get_sequence(self):
        return self.sequence

    def increment_sequence(self):
        self.sequence = self.sequence + 1
