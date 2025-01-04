from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from source.game_management.game_state import GameState


class Biome(str, Enum):
    """
    The four biomes a quad can be of.
    """
    DESERT = "DESERT"
    FOREST = "FOREST"
    SEA = "SEA"
    MOUNTAIN = "MOUNTAIN"


class ImprovementType(str, Enum):
    """
    The six types that an improvement can be of.
    """
    INDUSTRIAL = "INDUSTRIAL"
    MAGICAL = "MAGICAL"
    ECONOMICAL = "ECONOMICAL"
    BOUNTIFUL = "BOUNTIFUL"
    INTIMIDATORY = "INTIMIDATORY"
    PANDERING = "PANDERING"


class ProjectType(str, Enum):
    """
    The three types that a project can be of.
    """
    MAGICAL = "MAGICAL"
    ECONOMICAL = "ECONOMICAL"
    BOUNTIFUL = "BOUNTIFUL"


class HarvestStatus(str, Enum):
    """
    The three harvest statuses that are used to regulate harvest levels in a settlement.
    """
    POOR = "POOR"
    STANDARD = "STANDARD"
    PLENTIFUL = "PLENTIFUL"


class EconomicStatus(str, Enum):
    """
    The three economic statuses that are used to regulate wealth levels in a settlement.
    """
    RECESSION = "RECESSION"
    STANDARD = "STANDARD"
    BOOM = "BOOM"


class AttackPlaystyle(str, Enum):
    """
    The three AI attack playstyles; aggressive AIs essentially attack at every opportunity, defensive will almost never
    attack, and neutral AIs are in between.
    """
    AGGRESSIVE = "AGGRESSIVE"
    DEFENSIVE = "DEFENSIVE"
    NEUTRAL = "NEUTRAL"


class ExpansionPlaystyle(str, Enum):
    """
    The three AI expansion playstyles; expansionist AIs will create new settlements at level 3, neutral ones at level 5,
    and hermit ones at level 10.
    """
    EXPANSIONIST = "EXPANSIONIST"
    NEUTRAL = "NEUTRAL"
    HERMIT = "HERMIT"


class VictoryType(str, Enum):
    """
    The six different victory types. Their criteria for victory are below:
    - Elimination: all settlements belong to the player
    - Jubilation: maintain 100% satisfaction in at least 5 settlements for 25 turns
    - Gluttony: reach level 10 in at least 10 settlements
    - Affluence: accumulate 100k wealth over the course of the game
    - Vigour: construct the holy sanctum in a settlement
    - Serendipity: research the three pieces of ardour
    """
    ELIMINATION = "ELIMINATION"
    JUBILATION = "JUBILATION"
    GLUTTONY = "GLUTTONY"
    AFFLUENCE = "AFFLUENCE"
    VIGOUR = "VIGOUR"
    SERENDIPITY = "SERENDIPITY"


class Faction(str, Enum):
    """
    The fourteen different playable factions in Microcosm. Each faction has its own advantage and disadvantage.
    """
    AGRICULTURISTS = "Agriculturists"
    CAPITALISTS = "Capitalists"
    SCRUTINEERS = "Scrutineers"
    GODLESS = "The Godless"
    RAVENOUS = "The Ravenous"
    FUNDAMENTALISTS = "Fundamentalists"
    ORTHODOX = "The Orthodox"
    CONCENTRATED = "The Concentrated"
    FRONTIERSMEN = "Frontiersmen"
    IMPERIALS = "Imperials"
    PERSISTENT = "The Persistent"
    EXPLORERS = "Explorers"
    INFIDELS = "Infidels"
    NOCTURNE = "The Nocturne"


class InvestigationResult(str, Enum):
    """
    The types of result a relic investigation can yield.
    """
    WEALTH = "WEALTH"
    FORTUNE = "FORTUNE"
    VISION = "VISION"
    HEALTH = "HEALTH"
    POWER = "POWER"
    STAMINA = "STAMINA"
    UPKEEP = "UPKEEP"
    ORE = "ORE"
    TIMBER = "TIMBER"
    MAGMA = "MAGMA"
    NONE = "NONE"


class OverlayType(Enum):
    """
    The various overlay types that may be displayed.
    """
    STANDARD = "STANDARD"
    SETTLEMENT = "SETTLEMENT"
    CONSTRUCTION = "CONSTRUCTION"
    BLESSING = "BLESSING"
    DEPLOYMENT = "DEPLOYMENT"
    UNIT = "UNIT"
    TUTORIAL = "TUTORIAL"
    WARNING = "WARNING"
    BLESS_NOTIF = "BLESS_NOTIF"
    CONSTR_NOTIF = "CONSTR_NOTIF"
    LEVEL_NOTIF = "LEVEL_NOTIF"
    ATTACK = "ATTACK"
    HEAL = "HEAL"
    SETL_ATTACK = "SETL_ATTACK"
    SETL_CLICK = "SETL_CLICK"
    SIEGE_NOTIF = "SIEGE_NOTIF"
    PAUSE = "PAUSE"
    CONTROLS = "CONTROLS"
    VICTORY = "VICTORY"
    ELIMINATION = "ELIMINATION"
    CLOSE_TO_VIC = "CLOSE_TO_VIC"
    INVESTIGATION = "INVESTIGATION"
    NIGHT = "NIGHT"
    ACH_NOTIF = "ACH_NOTIF"
    PLAYER_CHANGE = "PLAYER_CHANGE"
    DESYNC = "DESYNC"


class SettlementAttackType(Enum):
    """
    The two types of attack on a settlement that a unit can execute.
    """
    ATTACK = "ATTACK"
    BESIEGE = "BESIEGE"


class PauseOption(Enum):
    """
    The four pause options available to the player.
    """
    RESUME = "RESUME"
    SAVE = "SAVE"
    CONTROLS = "CONTROLS"
    QUIT = "QUIT"


class ConstructionMenu(Enum):
    """
    The three different views the player is presented with when selecting a settlement's construction.
    """
    IMPROVEMENTS = "IMPROVEMENTS"
    PROJECTS = "PROJECTS"
    UNITS = "UNITS"


class StandardOverlayView(Enum):
    """
    The four different views the player is presented with when viewing the standard overlay.
    """
    BLESSINGS = "BLESSINGS"
    VAULT = "VAULT"
    SETTLEMENTS = "SETTLEMENTS"
    VICTORIES = "VICTORIES"


@dataclass
class Quad:
    """
    A quad on the board. Has a biome, yield, and whether it is selected.
    """
    biome: Biome
    wealth: int
    harvest: int
    zeal: int
    fortune: int
    location: Tuple[int, int]
    # Even though a quad will only ever have one resource, it's easier to use this.
    resource: Optional[ResourceCollection] = None
    selected: bool = False
    is_relic: bool = False


@dataclass
class FactionDetail:
    """
    Additional information about a faction.
    """
    faction: Faction
    lore: str
    buff: str
    debuff: str
    rec_victory_type: VictoryType


@dataclass
class Effect:
    """
    An effect that is generated on a settlement upon the completion of the construction of an improvement.
    """
    wealth: float = 0.0
    harvest: float = 0.0
    zeal: float = 0.0
    fortune: float = 0.0
    strength: float = 0.0
    satisfaction: float = 0.0


@dataclass
class Blessing:
    """
    A blessing that may be undergone to unlock improvements, unit plans, or achieve victory criteria.
    """
    name: str
    description: str
    cost: float  # Measured in fortune.


@dataclass
class Improvement:
    """
    An improvement that may be constructed in a settlement.
    """
    type: ImprovementType  # Corresponds to the highest yield in its effect.
    cost: float  # Measured in zeal.
    name: str
    description: str
    effect: Effect
    prereq: Optional[Blessing]
    # The construction of some improvements requires core resources to be used.
    req_resources: Optional[ResourceCollection] = None


@dataclass
class Project:
    """
    A project that may be worked on in a settlement.
    """
    type: ProjectType
    name: str
    description: str


@dataclass
class ResourceCollection:
    """
    A utility class representing a collection of resources. This is used for Quad, Settlement, and Player objects.
    """
    # Core resources
    ore: int = 0
    timber: int = 0
    magma: int = 0
    # Rare resources
    aurora: int = 0
    bloodstone: int = 0
    obsidian: int = 0
    sunstone: int = 0
    aquamarine: int = 0

    def __bool__(self) -> bool:
        """
        A custom truth value testing method - this exists so that we can do checks like `if quad.resource` without
        having to check each individual resource in the quad's collection.
        :return: Whether the collection has one or more resources of any type.
        """
        return bool(self.ore or self.timber or self.magma or
                    self.aurora or self.bloodstone or self.obsidian or self.sunstone or self.aquamarine)


@dataclass
class UnitPlan:
    """
    The plan for a unit that may be recruited.
    """
    power: float  # Used in attacks.
    max_health: float
    total_stamina: int
    name: str
    prereq: Optional[Blessing]
    cost: float  # Measured in zeal.
    can_settle: bool = False
    heals: bool = False


@dataclass
class DeployerUnitPlan(UnitPlan):
    """
    The plan for a deployer unit that may be recruited.
    """
    # This needs to have a default value since it's a subclass of UnitPlan, meaning this argument in the constructor
    # will come after the last UnitPlan attribute.
    max_capacity: int = 3


@dataclass
class Unit:
    """
    The actual instance of a unit, based on a UnitPlan.
    """
    health: float
    remaining_stamina: int
    location: Tuple[int, int]
    garrisoned: bool
    plan: UnitPlan
    has_acted: bool = False  # Units can only act (attack/heal) once per turn.
    besieging: bool = False


@dataclass
class DeployerUnit(Unit):
    """
    The actual instance of a deployer unit, based on a DeployerUnitPlan.
    """
    passengers: List[Unit] = field(default_factory=lambda: [])


@dataclass
class Heathen:
    """
    A roaming unit that doesn't belong to any player that will attack any unit it sees.
    """
    health: float
    remaining_stamina: int
    location: Tuple[int, int]
    plan: UnitPlan
    has_attacked: bool = False  # Heathens can also only attack once per turn.


@dataclass
class Construction:
    """
    An improvement being constructed, a project being worked on, or a unit being recruited currently in a settlement.
    """
    construction: Improvement | Project | UnitPlan
    zeal_consumed: float = 0.0


@dataclass
class OngoingBlessing:
    """
    A blessing being currently undergone.
    """
    blessing: Blessing
    fortune_consumed: float = 0.0


@dataclass
class Settlement:
    """
    A settlement belonging to a player.
    """
    name: str
    location: Tuple[int, int]
    improvements: List[Improvement]
    quads: List[Quad]  # Only players of The Concentrated faction can have more than one quad in a settlement.
    # Resources can be exploited by a settlement if they are within 1 quad.
    resources: ResourceCollection
    garrison: List[Unit]
    strength: float = 100.0
    max_strength: float = 100.0
    satisfaction: float = 50.0
    current_work: Optional[Construction] = None
    level: int = 1
    """
    The harvest reserves required for each upgrade is as below:
    Threshold = (current_level ^ 2) * 25
    Level 1 -> 2 = 25
    Level 2 -> 3 = 100
    Level 3 -> 4 = 225
    Level 4 -> 5 = 400
    Level 5 -> 6 = 625
    Level 6 -> 7 = 900
    Level 7 -> 8 = 1225
    Level 8 -> 9 = 1600
    Level 9 -> 10 = 2025
    """
    harvest_reserves: float = 0.0
    harvest_status: HarvestStatus = HarvestStatus.STANDARD
    economic_status: EconomicStatus = EconomicStatus.STANDARD
    produced_settler: bool = False  # Used for AI players so that settlements don't get stuck producing settlers.
    besieged: bool = False


@dataclass
class CompletedConstruction:
    """
    An improvement or unit plan construction that has been completed.
    """
    construction: Improvement | UnitPlan
    settlement: Settlement


@dataclass
class AIPlaystyle:
    """
    An overall playstyle for an AI player, encompassing both attacking and empire expansion.
    """
    attacking: AttackPlaystyle
    expansion: ExpansionPlaystyle


@dataclass
class Player:
    """
    A player of Microcosm.
    """
    name: str
    faction: Faction
    colour: int  # Refers to pyxel's colours, which resolve to integers.
    wealth: float = 0.0
    settlements: List[Settlement] = field(default_factory=lambda: [])
    units: List[Unit] = field(default_factory=lambda: [])
    blessings: List[Blessing] = field(default_factory=lambda: [])
    resources: ResourceCollection = field(default_factory=ResourceCollection)
    quads_seen: Set[Tuple[int, int]] = field(default_factory=set)
    imminent_victories: Set[VictoryType] = field(default_factory=set)
    ongoing_blessing: Optional[OngoingBlessing] = None
    ai_playstyle: Optional[AIPlaystyle] = None
    jubilation_ctr: int = 0  # How many turns the player has had 5 settlements at 100% satisfaction.
    accumulated_wealth: float = 0.0
    eliminated: bool = False


@dataclass
class AttackData:
    """
    The data from an attack that has occurred.
    """
    attacker: Unit | Heathen
    defender: Unit | Heathen
    damage_to_attacker: float
    damage_to_defender: float
    player_attack: bool
    attacker_was_killed: bool
    defender_was_killed: bool


@dataclass
class HealData:
    """
    The data from a healing action that has occurred.
    """
    healer: Unit
    healed: Unit
    heal_amount: float
    original_health: float
    player_heal: bool


@dataclass
class SetlAttackData:
    """
    The data from an attack on a settlement that has occurred.
    """
    attacker: Unit
    settlement: Settlement
    setl_owner: Player
    damage_to_attacker: float
    damage_to_setl: float
    player_attack: bool
    attacker_was_killed: bool
    setl_was_taken: bool


@dataclass
class GameConfig:
    """
    The configuration for a game of Microcosm.
    """
    player_count: int
    player_faction: Faction
    biome_clustering: bool
    fog_of_war: bool
    climatic_effects: bool
    multiplayer: bool


@dataclass
class Victory:
    """
    A victory achieved by a player.
    """
    player: Player
    type: VictoryType


@dataclass
class Statistics:
    """
    The statistics loaded from statistics.json.
    """
    playtime: float = 0.0
    turns_played: int = 0
    victories: Dict[VictoryType, int] = field(default_factory=lambda: {})
    defeats: int = 0
    factions: Dict[Faction, int] = field(default_factory=lambda: {})
    achievements: Set[str] = field(default_factory=set)


@dataclass
class Achievement:
    """
    An achievement that may be obtained by a player.
    """
    name: str
    description: str
    # The function to call to verify whether the achievement has been obtained.
    verification_fn: Callable[[GameState, Statistics], bool]
    # Whether this achievement can only be verified immediately after the player has won a game.
    post_victory: bool = False


@dataclass
class PlayerDetails:
    """
    The details for a player in a multiplayer game. Used by the server and in menus prior to joining a multiplayer game.
    """
    name: str
    faction: Faction
    id: Optional[int]  # None if the player is an AI.


@dataclass
class LobbyDetails:
    """
    The details for a multiplayer lobby for a prospective game or one currently in progress.
    """
    name: str
    current_players: List[PlayerDetails]
    cfg: GameConfig
    current_turn: Optional[int]  # None if the game hasn't started.


@dataclass
class LoadedMultiplayerState:
    """
    Keeps track of what game state has loaded in a multiplayer game. Used when loading or joining a multiplayer game.
    """
    quad_chunks_loaded: int = 0
    players_loaded: int = 0
    total_quads_seen: int = 0
    quads_seen_loaded: int = 0
    total_heathens: int = 0
    heathens_loaded: bool = False  # Only a boolean because we load all heathens at once.
