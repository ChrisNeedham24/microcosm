import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Tuple

from source.foundation.models import GameConfig, PlayerDetails, Faction, Settlement, LobbyDetails, \
    ResourceCollection, Construction, OngoingBlessing, InvestigationResult, Player, AIPlaystyle


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
    AUTOFILL = "AUTOFILL"


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
    identifier: Optional[int]


@dataclass
class CreateEvent(Event):
    cfg: GameConfig
    lobby_name: Optional[str] = None
    player_details: Optional[List[PlayerDetails]] = None


@dataclass
class InitEvent(Event):
    game_name: str
    until_night: Optional[int] = None
    cfg: Optional[GameConfig] = None
    quad_chunk: Optional[str] = None
    quad_chunk_idx: Optional[int] = None


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
    lobbies: Optional[List[LobbyDetails]] = None


@dataclass
class LeaveEvent(Event):
    lobby_name: str
    leaving_player_faction: Optional[Faction] = None
    player_ai_playstyle: Optional[AIPlaystyle] = None


@dataclass
class JoinEvent(Event):
    lobby_name: str
    player_faction: Faction
    lobby_details: Optional[LobbyDetails] = None
    until_night: Optional[int] = None
    nighttime_left: Optional[int] = None
    cfg: Optional[GameConfig] = None
    quad_chunk: Optional[str] = None
    quad_chunk_idx: Optional[int] = None
    player_chunk: Optional[str] = None
    player_chunk_idx: Optional[int] = None
    quads_seen_chunk: Optional[str] = None
    total_quads_seen: Optional[int] = None
    heathens_chunk: Optional[str] = None
    total_heathens: Optional[int] = None


@dataclass
class RegisterEvent(Event):
    port: int


@dataclass
class EndTurnEvent(Event):
    game_name: str
    player_faction: Faction
    ai_random_seed: Optional[int] = None


@dataclass
class UnreadyEvent(Event):
    game_name: str
    player_faction: Faction


@dataclass
class AutofillEvent(Event):
    lobby_name: str
    players: Optional[List[Player]] = None
