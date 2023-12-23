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
from source.foundation.models import GameConfig, Faction, Player
from source.game_management.game_state import GameState

HOST, PORT = "localhost", 9999


class EventType(Enum):
    CREATE = "CREATE"
    INIT = "INIT"
    UPDATE = "UPDATE"


@dataclass
class Event:
    type: EventType
    timestamp: datetime.datetime


@dataclass
class CreateEvent(Event):
    cfg: GameConfig


@dataclass
class InitEvent(Event):
    game_name: str
    players: typing.List[typing.Tuple[str, Faction]]


@dataclass
class UpdateEvent(Event):
    game_name: str


class RequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        evt: Event = json.loads(self.request[0])
        sock: socket.socket = self.request[1]
        self.process_event(evt)
        sock.sendto(b"Received", self.client_address)

    def process_event(self, evt: Event):
        if evt.type == EventType.CREATE:
            self.process_create_event(evt)
        elif evt.type == EventType.INIT:
            self.process_init_event(evt)
        elif evt.type == EventType.UPDATE:
            self.process_update_event(evt)

    def process_create_event(self, evt: CreateEvent):
        gsrs: typing.Dict[str, GameState] = self.server.game_states_ref
        lobby_name = random.choice(LOBBY_NAMES)
        while lobby_name in gsrs:
            lobby_name = random.choice(LOBBY_NAMES)
        player_name = random.choice(PLAYER_NAMES)
        gsrs[lobby_name] = GameState()
        gsrs[lobby_name].players.append(Player(player_name, evt.cfg.player_faction,
                                               FACTION_COLOURS[evt.cfg.player_faction]))
        # TODO How to get this data back to the player that made the lobby?

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


class EventListener:
    def __init__(self):
        self.game_states: typing.Dict[str, GameState] = {}
        self.events: typing.Dict[str, typing.List[Event]] = {}

    def run(self):
        with socketserver.UDPServer((HOST, PORT), RequestHandler) as server:
            server.game_states_ref = self.game_states
            server.events_ref = self.events
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
