from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Tuple

from source.foundation.models import GameConfig, PlayerDetails, Faction, Settlement, LobbyDetails, \
    ResourceCollection, Construction, OngoingBlessing, InvestigationResult, Player, AIPlaystyle


class EventType(str, Enum):
    """
    The different types of events that can be sent/received.
    """
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
    SAVE = "SAVE"
    QUERY_SAVES = "QUERY_SAVES"
    LOAD = "LOAD"
    KEEPALIVE = "KEEPALIVE"


class UpdateAction(str, Enum):
    """
    The different actions that may take place as part of update events.
    """
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
    """
    The base event class that all events inherit from.
    """
    type: EventType
    # A hash of the client's hardware address and PID, identifying the running instance. None when the server is
    # generating and sending events to clients.
    identifier: Optional[int]


@dataclass
class CreateEvent(Event):
    """
    The event containing the required data to create a multiplayer game.
    """
    cfg: GameConfig
    # The below are only populated when the server responds to the client with the created lobby and players.
    lobby_name: Optional[str] = None
    player_details: Optional[List[PlayerDetails]] = None


@dataclass
class InitEvent(Event):
    """
    The event containing the required data to initialise a multiplayer game.
    """
    game_name: str
    # The below are only populated when the server responds to all players with the initialised board details.
    until_night: Optional[int] = None
    cfg: Optional[GameConfig] = None
    quad_chunk: Optional[str] = None
    quad_chunk_idx: Optional[int] = None


@dataclass
class UpdateEvent(Event):
    """
    The base update event that all events that update game state inherit from.
    """
    action: UpdateAction
    game_name: str
    player_faction: Faction  # Used to identify the player taking the action.


@dataclass
class FoundSettlementEvent(UpdateEvent):
    """
    The event containing the required data to found a settlement.
    """
    # Generally we wouldn't serialise an entire object, but because the settlement has just been founded, it doesn't
    # have any improvements or anything that would make the serialised bytes too large to effectively send.
    settlement: Settlement
    from_settler: bool = True


@dataclass
class SetBlessingEvent(UpdateEvent):
    """
    The event containing the required data to set a player's blessing.
    """
    blessing: OngoingBlessing


@dataclass
class SetConstructionEvent(UpdateEvent):
    """
    The event containing the required data to set the construction in a settlement.
    """
    # Some improvements cost resources, and this is subtracted client-side, so we need to update the server and other
    # clients with any changes.
    player_resources: ResourceCollection
    settlement_name: str
    construction: Construction


@dataclass
class MoveUnitEvent(UpdateEvent):
    """
    The event containing the required data to move a unit.
    """
    initial_loc: Tuple[int, int]  # Used to identify the unit being moved.
    new_loc: Tuple[int, int]
    # The logic to subtract stamina and determine whether the unit is not besieging happens client-side, so we need to
    # update the server and other clients with the changes.
    new_stamina: int
    besieging: bool


@dataclass
class DeployUnitEvent(UpdateEvent):
    """
    The event containing the required data to deploy a unit from a settlement.
    """
    settlement_name: str
    location: Tuple[int, int]  # Refers to the deployed unit's location.


@dataclass
class GarrisonUnitEvent(UpdateEvent):
    """
    The event containing the required data to garrison a unit in a settlement.
    """
    initial_loc: Tuple[int, int]  # Used to identify the unit being garrisoned.
    # The logic to subtract stamina happens client-side, so we need to update the server and other clients with the
    # changes.
    new_stamina: int
    settlement_name: str


@dataclass
class InvestigateEvent(UpdateEvent):
    """
    The event containing the required data to investigate a relic with a unit.
    """
    unit_loc: Tuple[int, int]  # Used to identify the unit investigating the relic.
    relic_loc: Tuple[int, int]
    # We need to know the result so we can replicate the effects on the server and other clients.
    result: InvestigationResult


@dataclass
class BesiegeSettlementEvent(UpdateEvent):
    """
    The event containing the required data to place a settlement under siege.
    """
    unit_loc: Tuple[int, int]  # Used to identify the unit placing the settlement under siege.
    settlement_name: str


@dataclass
class BuyoutConstructionEvent(UpdateEvent):
    """
    The event containing the required data to buyout a settlement's construction.
    """
    settlement_name: str
    # The logic to subtract wealth happens client-side, so we need to update the server and other clients with the
    # changes.
    player_wealth: float


@dataclass
class DisbandUnitEvent(UpdateEvent):
    """
    The event containing the required data to disband a unit.
    """
    location: Tuple[int, int]  # Used to identify the unit being disbanded.


@dataclass
class AttackUnitEvent(UpdateEvent):
    """
    The event containing the required data to process a unit-based attack.
    """
    attacker_loc: Tuple[int, int]  # Used to identify the attacking unit.
    defender_loc: Tuple[int, int]  # Used to identify the defending unit.


@dataclass
class AttackSettlementEvent(UpdateEvent):
    """
    The event containing the required data to process a settlement-based attack.
    """
    attacker_loc: Tuple[int, int]  # Used to identify the attacking unit.
    settlement_name: str


@dataclass
class HealUnitEvent(UpdateEvent):
    """
    The event containing the required data to heal a unit.
    """
    healer_loc: Tuple[int, int]  # Used to identify the healer unit.
    healed_loc: Tuple[int, int]  # Used to identify the unit being healed.


@dataclass
class BoardDeployerEvent(UpdateEvent):
    """
    The event containing the required data to have a unit board a deployer unit.
    """
    initial_loc: Tuple[int, int]  # Used to identify the unit boarding the deployer unit.
    deployer_loc: Tuple[int, int]  # Used to identify the deployer unit.
    # The logic to subtract stamina happens client-side, so we need to update the server and other clients with the
    # changes.
    new_stamina: int


@dataclass
class DeployerDeployEvent(UpdateEvent):
    """
    The event containing the required data to deploy a unit from a deployer unit.
    """
    deployer_loc: Tuple[int, int]  # Used to identify the deployer unit.
    passenger_idx: int
    deployed_loc: Tuple[int, int]


@dataclass
class QueryEvent(Event):
    """
    The event containing the required data for a response to a query for the available multiplayer lobbies.
    This event is only populated when the server responds to the client with the available lobbies.
    """
    lobbies: Optional[List[LobbyDetails]] = None


@dataclass
class LeaveEvent(Event):
    """
    The event containing the required data for a player to leave a multiplayer game.
    """
    lobby_name: str
    # The below are only populated when the server responds to all players with the details regarding the player that
    # left and their replacement AI.
    leaving_player_faction: Optional[Faction] = None
    player_ai_playstyle: Optional[AIPlaystyle] = None


@dataclass
class JoinEvent(Event):
    """
    The event containing the required data for a player to join a multiplayer game.
    """
    lobby_name: str
    player_faction: Faction  # The faction the player is joining as.
    # The below are only populated when the server responds to the joining client with the game state details, or when
    # responding to other players with the details of the joining client.
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
    """
    The event containing the required data to register a client with the game server.
    """
    port: int  # The port the client has their event listener listening on - this is dynamic, so we need to keep track.


@dataclass
class EndTurnEvent(Event):
    """
    The event containing the required data to end a turn.
    """
    game_name: str
    # The below is only populated when the server responds to all players with the hash of the server's game state, for
    # synchronisation purposes.
    game_state_hash: Optional[int] = None


@dataclass
class UnreadyEvent(Event):
    """
    The event containing the required data to mark a player as no longer ready to end their turn.
    """
    game_name: str


@dataclass
class AutofillEvent(Event):
    """
    The event containing the required data to autofill a multiplayer lobby with AI players.
    """
    lobby_name: str
    # The below is only populated when the server responds to all players with the generated AI player details.
    players: Optional[List[Player]] = None


@dataclass
class SaveEvent(Event):
    """
    The event containing the required data to save a multiplayer game on the server.
    """
    game_name: str


@dataclass
class QuerySavesEvent(Event):
    """
    The event containing the required data for a response to a query for the available saved multiplayer games.
    This event is only populated when the server responds to the client with the available saved games.
    """
    saves: Optional[List[str]] = None


@dataclass
class LoadEvent(Event):
    """
    The event containing the required data to load a saved multiplayer game onto the game server.
    """
    save_name: str
    # The below is only populated when the server responds to the client with the created lobby for the loaded game.
    lobby: Optional[LobbyDetails] = None
