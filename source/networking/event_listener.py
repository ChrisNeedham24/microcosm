import datetime
import json
import random
import socket
import socketserver
import typing
from dataclasses import dataclass
from enum import Enum

from source.display.board import Board
from source.foundation.catalogue import FACTION_COLOURS, LOBBY_NAMES, PLAYER_NAMES
from source.foundation.models import GameConfig, Faction, Player, PlayerDetails, LobbyDetails
from source.game_management.game_controller import GameController
from source.game_management.game_state import GameState
from source.saving.save_encoder import ObjectConverter, SaveEncoder

HOST, SERVER_PORT, CLIENT_PORT = "localhost", 9999, 55555


class EventType(str, Enum):
    CREATE = "CREATE"
    INIT = "INIT"
    UPDATE = "UPDATE"
    QUERY = "QUERY"


@dataclass
class Event:
    type: EventType
    timestamp: datetime.datetime


@dataclass
class CreateEvent(Event):
    cfg: GameConfig
    creator_id: int
    lobby_name: typing.Optional[str] = None
    player_details: typing.Optional[typing.List[PlayerDetails]] = None
    until_night: typing.Optional[int] = None


@dataclass
class InitEvent(Event):
    game_name: str
    players: typing.List[typing.Tuple[str, Faction]]


@dataclass
class UpdateEvent(Event):
    game_name: str


@dataclass
class QueryEvent(Event):
    lobbies: typing.Optional[typing.List[LobbyDetails]] = None


class RequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        evt: Event = json.loads(self.request[0], object_hook=ObjectConverter)
        sock: socket.socket = self.request[1]
        self.process_event(evt, sock)

    def process_event(self, evt: Event, sock: socket.socket):
        if evt.type == EventType.CREATE:
            self.process_create_event(evt, sock)
        elif evt.type == EventType.INIT:
            self.process_init_event(evt)
        elif evt.type == EventType.UPDATE:
            self.process_update_event(evt)
        elif evt.type == EventType.QUERY:
            self.process_query_event(evt)

    def process_create_event(self, evt: CreateEvent, sock: socket.socket):
        gsrs: typing.Dict[str, GameState] = self.server.game_states_ref
        if self.server.is_server:
            lobby_name = random.choice(LOBBY_NAMES)
            while lobby_name in gsrs:
                lobby_name = random.choice(LOBBY_NAMES)
            player_name = random.choice(PLAYER_NAMES)
            gsrs[lobby_name] = GameState()
            gsrs[lobby_name].players.append(Player(player_name, evt.cfg.player_faction,
                                                   FACTION_COLOURS[evt.cfg.player_faction]))
            self.server.clients_ref[lobby_name] = \
                [PlayerDetails(player_name, evt.cfg.player_faction, evt.creator_id, self.client_address[0])]
            self.server.lobbies_ref[lobby_name] = evt.cfg
            resp_evt: CreateEvent = CreateEvent(evt.type, evt.timestamp, evt.cfg, evt.creator_id, lobby_name,
                                                self.server.clients_ref[lobby_name], gsrs[lobby_name].until_night)
            sock.sendto(json.dumps(resp_evt, cls=SaveEncoder).encode(), (self.client_address[0], CLIENT_PORT))
        else:
            gsrs["local"].until_night = evt.until_night
            gsrs["local"].players.append(Player(evt.player_details[0].name, evt.cfg.player_faction,
                                                FACTION_COLOURS[evt.cfg.player_faction]))
            gc: GameController = self.server.game_controller_ref
            gc.menu.multiplayer_lobby_name = evt.lobby_name
            gc.menu.multiplayer_player_details = evt.player_details

    def process_init_event(self, evt: InitEvent):
        gsrs: typing.Dict[str, GameState] = self.server.game_states_ref
        init_event: InitEvent = evt
        gsr: GameState = gsrs[init_event.game_name]
        gsr.game_started = True
        gsr.turn = 1
        random.seed()
        gsr.until_night = random.randint(10, 20)
        gsr.nighttime_left = 0
        gsr.on_menu = False
        for player in init_event.players:
            gsr.players.append(Player(player[0], player[1], FACTION_COLOURS[player[1]]))
        gsr.board = Board(init_event.cfg)

    def process_update_event(self, evt: UpdateEvent):
        self.server.events_ref.append(evt)

    def process_query_event(self, evt: Event, sock: socket.socket):
        if self.server.is_server:
            lobbies: typing.List[LobbyDetails] = []
            for name, cfg in self.lobbies_ref.items():
                lobbies.append(LobbyDetails(name, cfg))
            resp_evt: QueryEvent = QueryEvent(EventType.QUERY, datetime.datetime.now(), lobbies)
            sock.sendto(json.dumps(resp_evt, cls=SaveEncoder).encode(), (self.client_address[0], CLIENT_PORT))
        else:
            pass


class EventListener:
    def __init__(self, is_server: bool = False):
        self.game_states: typing.Dict[str, GameState] = {}
        self.events: typing.Dict[str, typing.List[Event]] = {}
        self.is_server: bool = is_server
        self.game_controller: typing.Optional[GameController] = None
        self.clients: typing.Dict[str, typing.List[PlayerDetails]] = {}
        self.lobbies: typing.Dict[str, GameConfig] = {}

    def run(self):
        with socketserver.UDPServer((HOST, SERVER_PORT if self.is_server else CLIENT_PORT), RequestHandler) as server:
            server.game_states_ref = self.game_states
            server.events_ref = self.events
            server.is_server = self.is_server
            server.game_controller_ref = self.game_controller
            server.clients_ref = self.clients
            server.lobbies_ref = self.lobbies
            server.serve_forever()


"""
Things to be initialised after the lobby is created:
- Turn
- Until night
- Nighttime left
- Players
- Board
- AIs (if any)
"""
