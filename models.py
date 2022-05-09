import typing
from dataclasses import dataclass
from enum import Enum


class Biome(Enum):
    DESERT = "DESERT",
    FOREST = "FOREST",
    SEA = "SEA",
    MOUNTAIN = "MOUNTAIN"


class ImprovementType(Enum):
    INDUSTRIAL = "INDUSTRIAL",
    MAGICAL = "MAGICAL",
    ECONOMICAL = "ECONOMICAL",
    BOUNTIFUL = "BOUNTIFUL",
    INTIMIDATORY = "INTIMIDATORY",
    PANDERING = "PANDERING"


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


@dataclass
class Unit:
    health: float
    remaining_stamina: int
    location: (float, float)
    garrisoned: bool
    plan: UnitPlan


@dataclass
class Construction:
    construction: typing.Union[Improvement, UnitPlan]
    zeal_consumed: float = 0.0


@dataclass
class OngoingBlessing:
    blessing: Blessing
    fortune_consumed: float = 0.0

# TODO Re-add settlement level, use harvest for it, some modifier to overall counts

@dataclass
class Settlement:
    name: str
    improvements: typing.List[Improvement]
    strength: float
    satisfaction: float
    location: (int, int)
    quads: typing.List[Quad]
    garrison: typing.List[Unit]
    current_work: typing.Optional[Construction]


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
    ongoing_blessing: typing.Optional[OngoingBlessing] = None
