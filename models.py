import random
import typing
from dataclasses import dataclass
from enum import Enum


class Biome(str, Enum):
    DESERT = "DESERT"
    FOREST = "FOREST"
    SEA = "SEA"
    MOUNTAIN = "MOUNTAIN"


class ImprovementType(str, Enum):
    INDUSTRIAL = "INDUSTRIAL"
    MAGICAL = "MAGICAL"
    ECONOMICAL = "ECONOMICAL"
    BOUNTIFUL = "BOUNTIFUL"
    INTIMIDATORY = "INTIMIDATORY"
    PANDERING = "PANDERING"


class HarvestStatus(str, Enum):
    POOR = "POOR"
    STANDARD = "STANDARD"
    PLENTIFUL = "PLENTIFUL"


class EconomicStatus(str, Enum):
    RECESSION = "RECESSION"
    STANDARD = "STANDARD"
    BOOM = "BOOM"


class AIPlaystyle(str, Enum):
    AGGRESSIVE = "AGGRESSIVE"
    DEFENSIVE = "DEFENSIVE"
    NEUTRAL = "NEUTRAL"


class VictoryType(Enum):
    ELIMINATION = "ELIMINATION"
    JUBILATION = "JUBILATION"
    GLUTTONY = "GLUTTONY"
    AFFLUENCE = "AFFLUENCE"
    VIGOUR = "VIGOUR"
    SERENDIPITY = "SERENDIPITY"


@dataclass
class Quad:
    biome: Biome
    wealth: float
    harvest: float
    zeal: float
    fortune: float
    selected: bool = False


@dataclass
class Effect:
    wealth: float = 0.0
    harvest: float = 0.0
    zeal: float = 0.0
    fortune: float = 0.0
    strength: float = 0.0
    satisfaction: float = 0.0


@dataclass
class Blessing:
    name: str
    description: str
    cost: float


@dataclass
class Improvement:
    type: ImprovementType
    cost: float
    name: str
    description: str
    effect: Effect
    prereq: typing.Optional[Blessing]


@dataclass
class UnitPlan:
    power: float
    max_health: float
    total_stamina: int
    name: str
    prereq: typing.Optional[Blessing]
    cost: float
    can_settle: bool = False


@dataclass
class Unit:
    health: float
    remaining_stamina: int
    location: (float, float)
    garrisoned: bool
    plan: UnitPlan
    has_attacked: bool = False
    sieging: bool = False


@dataclass
class Heathen:
    health: float
    remaining_stamina: int
    location: (float, float)
    plan: UnitPlan
    has_attacked: bool = False


@dataclass
class Construction:
    construction: typing.Union[Improvement, UnitPlan]
    zeal_consumed: float = 0.0


@dataclass
class OngoingBlessing:
    blessing: Blessing
    fortune_consumed: float = 0.0


@dataclass
class Settlement:
    name: str
    location: (int, int)
    improvements: typing.List[Improvement]
    quads: typing.List[Quad]
    garrison: typing.List[Unit]
    strength: float = 100
    max_strength: float = 100
    satisfaction: float = 50
    current_work: typing.Optional[Construction] = None
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
    level: int = 1
    harvest_reserves: float = 0.0
    harvest_status: HarvestStatus = HarvestStatus.STANDARD
    economic_status: EconomicStatus = EconomicStatus.STANDARD
    produced_settler: bool = False
    under_siege_by: typing.Optional[Unit] = None


@dataclass
class CompletedConstruction:
    construction: typing.Union[Improvement, UnitPlan]
    settlement: Settlement


@dataclass
class Player:
    name: str
    colour: int  # Refers to pyxel's colours, which resolve to integers.
    wealth: float
    settlements: typing.List[Settlement]
    units: typing.List[Unit]
    blessings: typing.List[Blessing]
    quads_seen: typing.Set[typing.Tuple[int, int]]
    ongoing_blessing: typing.Optional[OngoingBlessing] = None
    ai_playstyle: typing.Optional[AIPlaystyle] = None
    jubilation_ctr: int = 0
    accumulated_wealth: float = 0.0


@dataclass
class AttackData:
    attacker: typing.Union[Unit, Heathen]
    defender: typing.Union[Unit, Heathen]
    damage_to_attacker: float
    damage_to_defender: float
    player_attack: bool
    attacker_was_killed: bool
    defender_was_killed: bool


@dataclass
class SetlAttackData:
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
    player_count: int
    player_colour: int  # Refers to pyxel's colours, which resolve to integers.
    biome_clustering: bool
    fog_of_war: bool


@dataclass
class SaveFile:
    quads: typing.List[Quad]
    players: typing.List[Player]
    heathens: typing.List[Heathen]
    turn: int
    cfg: GameConfig


@dataclass
class Victory:
    player: Player
    type: VictoryType
