from random import randint, choice
from typing import List

from game.models.Cell import Cell, FieldTypes


# x nach rechts
# y nach oben
# nullpunkt unten rechts
# d.h. im array [X][Y]


class Grid(object):
    def __init__(self, width: int, height: int, item_number: int):
        self.width: int = width
        self.height: int = height
        self.item_number: int = item_number
        self.cells: List[List[Cell]] = []
        self._generate_grid()
        self._generate_rocks()
        self._generate_items()

    def get_random_cell(self) -> Cell:
        return self.cells[randint(0, self.height - 1)][randint(0, self.width - 1)]

    def _generate_items(self):
        item_count = 0
        while self.item_number != item_count:
            cell = self.get_random_cell()
            if not cell.player and not cell.field_type == FieldTypes.ROCK:
                cell.item = 1
                item_count = item_count + 1

    def _generate_grid(self):
        for y in range(self.height):
            self.cells.append([])
            for x in range(self.width):
                self.cells[y].append(Cell())

    def _generate_rocks(self, pct=0.3):
        for i in range(int(self.height * self.width * pct) // 2):
            x = randint(1, self.width - 1)
            y = randint(1, self.height - 1)

            # This check is stupid, but works
            if x < len(self.cells) \
                    and x + 1 < len(self.cells) \
                    and x - 1 < len(self.cells) \
                    and y < len(self.cells[x]) \
                    and y + 1 < len(self.cells[x]) \
                    and y - 1 < len(self.cells[x]):
                self.cells[y][x].field_type = FieldTypes.ROCK
                self.cells[y + choice([-1, 0, 1])][x + choice([-1, 0, 1])].field_type = FieldTypes.ROCK
