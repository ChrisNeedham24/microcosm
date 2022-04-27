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
    BOUNTIFUL = "BOUNTIFUL"


@dataclass
class Quad:
    biome: Biome
    wealth: float
    harvest: float
    zeal: float
    fortune: float


@dataclass
class Effect:
    wealth: float
    harvest: float
    zeal: float
    fortune: float
    satisfaction: float


@dataclass
class Improvement:
    type: ImprovementType
    cost: float
    name: str
    description: str
    effects: typing.List[Effect]


@dataclass
class Settlement:
    name: str
    improvements: typing.List[Improvement]
    level: int
    strength: float
