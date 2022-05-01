import random

from models import Biome


def calculate_yield_for_quad(biome: Biome) -> (float, float, float, float):
    # Returns tuple with wealth, harvest, zeal, and fortune.
    wealth: float = 0
    harvest: float = 0
    zeal: float = 0
    fortune: float = 0

    if biome is Biome.FOREST:
        wealth = random.uniform(0.0, 2.0)
        harvest = random.uniform(5.0, 10.0)
        zeal = random.uniform(1.0, 4.0)
        fortune = random.uniform(3.0, 6.0)
    elif biome is Biome.SEA:
        wealth = random.uniform(1.0, 4.0)
        harvest = random.uniform(3.0, 6.0)
        zeal = random.uniform(0.0, 1.0)
        fortune = random.uniform(5.0, 10.0)
    elif biome is Biome.DESERT:
        wealth = random.uniform(5.0, 10.0)
        harvest = random.uniform(0.0, 1.0)
        zeal = random.uniform(3.0, 6.0)
        fortune = random.uniform(1.0, 4.0)
    elif biome is Biome.MOUNTAIN:
        wealth = random.uniform(3.0, 6.0)
        harvest = random.uniform(1.0, 4.0)
        zeal = random.uniform(5.0, 10.0)
        fortune = random.uniform(0.0, 2.0)

    return wealth, harvest, zeal, fortune


def clamp(number: int, min_val: int, max_val: int) -> int:
    return max(min(max_val, number), min_val)
