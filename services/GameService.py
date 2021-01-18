import json

from config import PAYLOAD_DELIMITER
from game.models.Game import Movement, Game
from game.models.Player import Player
from models.Host import Host, HostType
from services.SocketService import SocketService

wrong_insert = "Wrong please type in: up, down, left, right"


class GameService:
    def __init__(self, socket_service: SocketService, all_host_group):
        self.games = []
        self.all_host_group = all_host_group
        self.socket_service = socket_service

    def get_game_for_player_id(self, player_id):
        for game in self.games:
            player = game.get_player(player_id)
            if player:
                return game
        return None

    def on_unicast_received(self, host, method, message):
        if method == "GS":
            self.on_command_received(host, message)
        if method == "GS/SYNC_GAMES":
            for game in self.games:
                self.socket_service.send_unicast(host, "GS/SYNC", game.to_pickle())
        if method == "GS/SYNC":
            game = Game.from_pickle(message)

            if not game:
                return
            if game not in self.games:
                self.games.append(game)

    def on_multicast_received(self, host, method, message):
        if method == "MAIN_GROUP/HOSTS":
            hosts = json.loads(message)
            list_of_hosts = [Host.from_json(h) for h in hosts]
            client_ids = [client.id for client in list_of_hosts if client.host_type == HostType.CLIENT]
            for game in self.games:
                removed = False
                t_players = []
                for player in game.players:
                    if player.id in client_ids:
                        p = game.get_player(player.id)
                        t_players.append(p)
                    else:
                        posx, posy = game.get_player_position(player)
                        game.grid.cells[posy][posx].player = None
                        removed = True
                game.players = t_players

                if removed:
                    self.send_game(game)

        if method == "GS/OV":
            game = Game.from_pickle(message)
            if not game:
                return
            if game not in self.games:
                print("FOUND NEW GAME!")
                self.games.append(game)

            for i, _game in enumerate(self.games):
                if _game.id == game.id and _game.seq + 1 == game.seq:
                    self.games[i] = game

    def on_command_received(self, host, payload):
        try:
            chunks = payload.split(PAYLOAD_DELIMITER)
            player_id = host.id
            mode = chunks[0]
            if mode == "create" and chunks[1] != "" or mode == "Create" and chunks[1] != "":
                game = Game(chunks[1], width=5, height=5, item_number=2)
                self.games.append(game)
                print(f"Created game {game.name}")
                self.send_game(game)
            elif mode == "display" or mode == "Display":
                game_names = []

                for game in self.games:
                    game_names.append(game.name)

                game_str = "\n".join(game_names)

                self.socket_service.send_unicast(host, "GS/LS", "Open games:\n" + game_str)
            elif mode == "leave" or mode == "Leave":
                game = self.get_game_for_player_id(player_id)
                if not game:
                    self.socket_service.send_unicast(host, "GS/ERROR", f"User is not in a game")
                    return
                player = game.get_player(player_id)
                game.remove_player(player)
                print(f"Player {player.name} left game {game.name}")
                self.send_game(game)
            elif len(chunks) == 3 and (mode == "join" or mode == "Join"):
                player_name = chunks[2]
                gamename = chunks[1]

                game = self.get_game_for_player_id(player_id)
                if game:
                    self.socket_service.send_unicast(host, "GS/ERROR", f"User is already in game {game.name}")
                    return

                game = next((game for game in self.games if gamename == game.name), None)
                if not game:
                    self.socket_service.send_unicast(host, "GS/ERROR", f"Could not find game with name {gamename}")
                game.add_player(Player(id=player_id, name=player_name))
                print(f"Player {player_name} joined game {game.name}")
                self.send_game(game)
            elif mode in [Movement.UP, Movement.DOWN, Movement.LEFT, Movement.RIGHT]:
                game = self.get_game_for_player_id(player_id)
                if not game:
                    self.socket_service.send_unicast(host, "GS/ERROR", "You are not joined the Game")
                    return
                player = game.get_player(player_id)
                if player:
                    game.move_player(player, mode)
                    print(f"Player {player.name} moved {mode}")
                    self.send_answer(host, game, player)
            else:
                self.socket_service.send_unicast(host, "GS/ERROR", wrong_insert)
        except Exception as e:
            print(e)
            self.socket_service.send_unicast(host, "GS/ERROR", "Ups, Something went wrong ;)")

    def has_player_won(self, player: Player):
        return len(player.items) >= 3

    def send_game(self, game):
        game.seq = game.seq + 1
        self.socket_service.send_group_multicast(self.all_host_group, "GS/OV", game.to_pickle())

    def send_answer(self, host: Host, game: Game, player: Player):
        if self.has_player_won(player):
            self.socket_service.send_group_multicast(self.all_host_group, "GS/WIN",
                                                     json.dumps({
                                                         'game_id': game.id,
                                                         'message': player.name + " has Won!!",
                                                     }))
        else:
            self.send_game(game)
