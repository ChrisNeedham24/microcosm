import random
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
    location: (float, float)


@dataclass
class Unit:
    strength: float
    power: float
    health: float
    location: (float, float)


class Player:
    name: str
    colour: int  # Refers to pyxel's colours, which resolve to integers.
    settlements: typing.List[Settlement]
    units: typing.List[Unit]

    def __init__(self, name: str, colour: int):
        self.name = name
        self.colour = colour
        location: (float, float) = (random.uniform(40, 80), random.uniform(30, 70))
        self.settlements = [Settlement("Protevousa", [], 1, 100, location)]
        self.units = [Unit(25, 25, 25, (location[0] - 20, location[1] - 20))]
