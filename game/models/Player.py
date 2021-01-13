import string


class Player(object):
    id = None
    name = None

    def __init__(self, id, name: string):
        self.id = id
        self.name = name
        self.items = []

