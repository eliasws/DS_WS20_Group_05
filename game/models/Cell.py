class FieldTypes:
    FIELD = "FIELD"
    ROCK = "ROCK"


class Cell(object):
    def __init__(self):
        self.item = 0
        self.field_type = FieldTypes.FIELD
        self.player = None
