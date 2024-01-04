import datetime
import typing
from dataclasses import dataclass
from enum import Enum

from source.foundation.models import GameConfig, PlayerDetails, Faction, Settlement, LobbyDetails, Blessing, \
    ResourceCollection, Construction, OngoingBlessing


class EventType(str, Enum):
    CREATE = "CREATE"
    INIT = "INIT"
    UPDATE = "UPDATE"
    QUERY = "QUERY"
    LEAVE = "LEAVE"
    JOIN = "JOIN"
    REGISTER = "REGISTER"


class UpdateAction(str, Enum):
    FOUND_SETTLEMENT = "FS"
    SET_BLESSING = "SB"
    SET_CONSTRUCTION = "SC"


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


@dataclass
class InitEvent(Event):
    game_name: str
    until_night: typing.Optional[int] = None
    cfg: typing.Optional[GameConfig] = None
    quad_chunk: typing.Optional[str] = None
    quad_chunk_idx: typing.Optional[int] = None


@dataclass
class UpdateEvent(Event):
    action: UpdateAction
    game_name: str
    player_faction: Faction


@dataclass
class FoundSettlementEvent(UpdateEvent):
    settlement: Settlement


@dataclass
class SetBlessingEvent(UpdateEvent):
    blessing: OngoingBlessing


@dataclass
class SetConstructionEvent(UpdateEvent):
    player_resources: ResourceCollection
    settlement_name: str
    construction: Construction


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
    player_details: typing.Optional[typing.List[PlayerDetails]] = None


@dataclass
class RegisterEvent(Event):
    port: int
