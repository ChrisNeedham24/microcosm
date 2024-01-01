import datetime
import json
import os
import random
import socket
import socketserver
import typing
import uuid
from dataclasses import dataclass
from enum import Enum

from source.display.board import Board
from source.foundation.catalogue import FACTION_COLOURS, LOBBY_NAMES, PLAYER_NAMES
from source.foundation.models import GameConfig, Faction, Player, PlayerDetails, LobbyDetails
from source.game_management.game_controller import GameController
from source.game_management.game_state import GameState
from source.networking.client import dispatch_event
from source.saving.save_encoder import ObjectConverter, SaveEncoder

HOST, SERVER_PORT, CLIENT_PORT = "localhost", 9999, 55555


class EventType(str, Enum):
    CREATE = "CREATE"
    INIT = "INIT"
    UPDATE = "UPDATE"
    QUERY = "QUERY"
    LEAVE = "LEAVE"
    JOIN = "JOIN"
    REGISTER = "REGISTER"


@dataclass
class Event:
    type: EventType
    timestamp: datetime.datetime
    # A hash of the client's hardware address and PID, identifying the running instance.
    identifier: typing.Optional[int]


@dataclass
class CreateEvent(Event):
    cfg: GameConfig
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


@dataclass
class LeaveEvent(Event):
    lobby_name: str


@dataclass
class JoinEvent(Event):
    lobby_name: str
    player_faction: Faction
    player_name: typing.Optional[str] = None


@dataclass
class RegisterEvent(Event):
    port: int


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
            self.process_query_event(evt, sock)
        elif evt.type == EventType.LEAVE:
            self.process_leave_event(evt)
        elif evt.type == EventType.JOIN:
            self.process_join_event(evt, sock)
        elif evt.type == EventType.REGISTER:
            self.process_register_event(evt)

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
            self.server.game_clients_ref[lobby_name] = \
                [PlayerDetails(player_name, evt.cfg.player_faction, evt.identifier, self.client_address[0])]
            self.server.lobbies_ref[lobby_name] = evt.cfg
            resp_evt: CreateEvent = CreateEvent(evt.type, evt.timestamp, None, evt.cfg, evt.identifier, lobby_name,
                                                self.server.game_clients_ref[lobby_name], gsrs[lobby_name].until_night)
            sock.sendto(json.dumps(resp_evt, cls=SaveEncoder).encode(), self.server.clients_ref[evt.identifier])
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

    def process_query_event(self, evt: QueryEvent, sock: socket.socket):
        if self.server.is_server:
            lobbies: typing.List[LobbyDetails] = []
            for name, cfg in self.server.lobbies_ref.items():
                lobbies.append(LobbyDetails(name, self.server.game_clients_ref[name], cfg))
            resp_evt: QueryEvent = QueryEvent(EventType.QUERY, datetime.datetime.now(), None, lobbies)
            sock.sendto(json.dumps(resp_evt, cls=SaveEncoder).encode(), self.server.clients_ref[evt.identifier])
        else:
            gc: GameController = self.server.game_controller_ref
            gc.menu.multiplayer_lobbies = evt.lobbies

    def process_leave_event(self, evt: LeaveEvent):
        old_clients = self.server.game_clients_ref[evt.lobby_name]
        new_clients = [client for client in old_clients if client.id != evt.identifier]
        self.server.game_clients_ref[evt.lobby_name] = new_clients
        if not new_clients:
            self.server.game_clients_ref.pop(evt.lobby_name)
            self.server.lobbies_ref.pop(evt.lobby_name)
            self.server.game_states_ref.pop(evt.lobby_name)

    def process_join_event(self, evt: JoinEvent, sock: socket.socket):
        if self.server.is_server:
            gsrs: typing.Dict[str, GameState] = self.server.game_states_ref
            player_name = random.choice(PLAYER_NAMES)
            while any(player.name == player_name for player in self.server.game_clients_ref[evt.lobby_name]):
                player_name = random.choice(PLAYER_NAMES)
            gsrs[evt.lobby_name].players.append(Player(player_name, evt.player_faction,
                                                       FACTION_COLOURS[evt.player_faction]))
            self.server.game_clients_ref[evt.lobby_name].append([PlayerDetails(player_name, evt.player_faction,
                                                                               evt.identifier, self.client_address[0])])
            resp_evt: JoinEvent = JoinEvent(EventType.JOIN, datetime.datetime.now(), None, evt.lobby_name,
                                            evt.identifier, evt.player_faction, player_name)
            sock.sendto(json.dumps(resp_evt, cls=SaveEncoder).encode(), self.server.clients_ref[evt.identifier])
        else:
            pass
    
    def process_register_event(self, evt: RegisterEvent):
        self.server.clients_ref[evt.identifier] = self.client_address[0], evt.port


class EventListener:
    def __init__(self, is_server: bool = False):
        self.game_states: typing.Dict[str, GameState] = {}
        self.events: typing.Dict[str, typing.List[Event]] = {}
        self.is_server: bool = is_server
        self.game_controller: typing.Optional[GameController] = None
        self.game_clients: typing.Dict[str, typing.List[PlayerDetails]] = {}
        self.lobbies: typing.Dict[str, GameConfig] = {}
        self.clients: typing.Dict[int, typing.Tuple[str, int]] = {}  # Hash identifier to (host, port).

    def run(self):
        with socketserver.UDPServer((HOST, SERVER_PORT if self.is_server else 0), RequestHandler) as server:
            if not self.is_server:
                dispatch_event(RegisterEvent(EventType.REGISTER, datetime.datetime.now(),
                                             hash((uuid.getnode(), os.getpid())), server.server_address[1]))
            server.game_states_ref = self.game_states
            server.events_ref = self.events
            server.is_server = self.is_server
            server.game_controller_ref = self.game_controller
            server.game_clients_ref = self.game_clients
            server.lobbies_ref = self.lobbies
            server.clients_ref = self.clients
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
