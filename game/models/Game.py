import ast
import json
import pickle
import string
import uuid
from typing import List, Tuple

from game.models.Grid import Grid, FieldTypes
from game.models.Player import Player


class Movement:
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


class Game(object):

    def __init__(self, name: string, width: int, height: int, item_number: int):
        self.id = uuid.uuid1()
        self.name: str = name
        self.seq = 0
        self.players: List[Player] = []
        self.grid: Grid = Grid(width, height, item_number)

    def add_player(self, player):
        if len(self.players) <= min(self.grid.width, self.grid.height):
            self.players.append(player)

            while True:
                random_cell = self.grid.get_random_cell()
                if not random_cell.player and not random_cell.field_type == FieldTypes.ROCK and not random_cell.item:
                    random_cell.player = player
                    break

            return True
        else:
            return False

    def remove_player(self, player):
        self.players.remove(player)
        return True

    def get_player(self, player_id):
        return next((player for player in self.players if str(player.id) == str(player_id)), None)

    def move_player(self, player: Player, movement: Movement):
        pos_x, pos_y = self.get_player_position(player)
        if movement == Movement.UP:
            self.set_player_position(player, pos_x, pos_y, pos_x, pos_y - 1)
        elif movement == Movement.DOWN:
            self.set_player_position(player, pos_x, pos_y, pos_x, pos_y + 1)
        elif movement == Movement.LEFT:
            self.set_player_position(player, pos_x, pos_y, pos_x - 1, pos_y)
        elif movement == Movement.RIGHT:
            self.set_player_position(player, pos_x, pos_y, pos_x + 1, pos_y)

    def set_player_position(self, player, current_x, current_y, position_x, position_y):
        if position_x > self.grid.width - 1 or position_x < 0:
            return False
        if position_y > self.grid.height - 1 or position_y < 0:
            return False
        # Check above already ensures array size
        cell = self.grid.cells[position_y][position_x]

        if cell.field_type == FieldTypes.ROCK:
            return False

        if cell.player:
            return False

        if cell.item:
            player.items.append(cell.item)
            cell.item = None

        current_cell = self.grid.cells[current_y][current_x]
        current_cell.player = None
        cell.player = player

        return True

    def get_player_position(self, player) -> Tuple[int, int]:
        for index_y, row in enumerate(self.grid.cells):
            for index_x, cell in enumerate(row):
                if cell.player and cell.player.id == player.id:
                    return index_x, index_y

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)

    def to_pickle(self):
        return pickle.dumps(self)

    @staticmethod
    def from_json(data: str):
        return json.loads(data, object_hook=lambda o: Game(**o))

    @staticmethod
    def from_pickle(data):
        try:
            return pickle.loads(data)
        except Exception as e:
            return pickle.loads(ast.literal_eval(data))

    def draw(self):
        print(self.to_string())

    def to_string(self):
        display_string = ''
        players = ''
        for index_y, row in enumerate(self.grid.cells):
            for index_x, cell in enumerate(row):
                if cell.field_type == FieldTypes.ROCK:
                    display_string += ' #  '
                elif cell.player:
                    display_string += ' [] '
                    players += cell.player.name + ":" + f"[{index_x}, {index_y}] items: {len(cell.player.items)}\n"
                elif cell.item:
                    display_string += ' X  '
                else:
                    display_string += ' .  '
            display_string += '\n'
        display_string += '\n'
        display_string += players
        return display_string

    def __eq__(self, other):
        return self.id == other.id
