import datetime
import typing
from dataclasses import dataclass
from enum import Enum

from source.foundation.models import GameConfig, PlayerDetails, Faction, Settlement, LobbyDetails, Blessing, \
    ResourceCollection, Construction, OngoingBlessing, InvestigationResult


class EventType(str, Enum):
    CREATE = "CREATE"
    INIT = "INIT"
    UPDATE = "UPDATE"
    QUERY = "QUERY"
    LEAVE = "LEAVE"
    JOIN = "JOIN"
    REGISTER = "REGISTER"
    END_TURN = "END_TURN"
    UNREADY = "UNREADY"


class UpdateAction(str, Enum):
    FOUND_SETTLEMENT = "FS"
    SET_BLESSING = "SB"
    SET_CONSTRUCTION = "SC"
    MOVE_UNIT = "MU"
    DEPLOY_UNIT = "DEU"
    GARRISON_UNIT = "GU"
    INVESTIGATE = "I"
    BESIEGE_SETTLEMENT = "BS"
    BUYOUT_CONSTRUCTION = "BC"
    DISBAND_UNIT = "DIU"
    ATTACK_UNIT = "AU"
    ATTACK_SETTLEMENT = "AS"
    HEAL_UNIT = "HU"
    BOARD_DEPLOYER = "BD"
    DEPLOYER_DEPLOY = "DD"


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
    from_settler: bool = True


@dataclass
class SetBlessingEvent(UpdateEvent):
    blessing: OngoingBlessing


@dataclass
class SetConstructionEvent(UpdateEvent):
    player_resources: ResourceCollection
    settlement_name: str
    construction: Construction


@dataclass
class MoveUnitEvent(UpdateEvent):
    initial_loc: (int, int)
    new_loc: (int, int)
    new_stamina: int
    besieging: bool


@dataclass
class DeployUnitEvent(UpdateEvent):
    settlement_name: str
    location: (int, int)


@dataclass
class GarrisonUnitEvent(UpdateEvent):
    initial_loc: (int, int)
    new_stamina: int
    settlement_name: str


@dataclass
class InvestigateEvent(UpdateEvent):
    unit_loc: (int, int)
    relic_loc: (int, int)
    result: InvestigationResult


@dataclass
class BesiegeSettlementEvent(UpdateEvent):
    unit_loc: (int, int)
    settlement_name: str


@dataclass
class BuyoutConstructionEvent(UpdateEvent):
    settlement_name: str
    player_wealth: float


@dataclass
class DisbandUnitEvent(UpdateEvent):
    location: (int, int)


@dataclass
class AttackUnitEvent(UpdateEvent):
    attacker_loc: (int, int)
    defender_loc: (int, int)


@dataclass
class AttackSettlementEvent(UpdateEvent):
    attacker_loc: (int, int)
    settlement_name: str


@dataclass
class HealUnitEvent(UpdateEvent):
    healer_loc: (int, int)
    healed_loc: (int, int)


@dataclass
class BoardDeployerEvent(UpdateEvent):
    initial_loc: (int, int)
    deployer_loc: (int, int)
    new_stamina: int


@dataclass
class DeployerDeployEvent(UpdateEvent):
    deployer_loc: (int, int)
    passenger_idx: int
    deployed_loc: (int, int)


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


@dataclass
class EndTurnEvent(Event):
    game_name: str
    player_faction: Faction
    new_heathen_loc: typing.Optional[typing.Tuple[int, int]] = None
    new_nighttime_left: typing.Optional[int] = None
    new_until_night: typing.Optional[int] = None


@dataclass
class UnreadyEvent(Event):
    game_name: str
    player_faction: Faction
