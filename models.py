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
    prereq: Blessing or None


@dataclass
class Unit:
    power: float
    health: float
    stamina: int
    location: (float, float)
    garrisoned: bool


@dataclass
class Settlement:
    name: str
    improvements: typing.List[Improvement]
    strength: float
    satisfaction: float
    location: (int, int)
    quads: typing.List[Quad]
    garrison: typing.List[Unit]


@dataclass
class Player:
    name: str
    colour: int  # Refers to pyxel's colours, which resolve to integers.
    settlements: typing.List[Settlement]
    units: typing.List[Unit]
    blessings: typing.List[Blessing]
