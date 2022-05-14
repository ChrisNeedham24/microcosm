import random
import typing

from models import Biome, Unit, Heathen, AttackData, Player, EconomicStatus, HarvestStatus


def calculate_yield_for_quad(biome: Biome) -> (float, float, float, float):
    # Returns tuple with wealth, harvest, zeal, and fortune.
    wealth: float = 0
    harvest: float = 0
    zeal: float = 0
    fortune: float = 0

    if biome is Biome.FOREST:
        wealth = random.uniform(0.0, 2.0)
        harvest = random.uniform(5.0, 9.0)
        zeal = random.uniform(1.0, 4.0)
        fortune = random.uniform(3.0, 6.0)
    elif biome is Biome.SEA:
        wealth = random.uniform(1.0, 4.0)
        harvest = random.uniform(3.0, 6.0)
        zeal = random.uniform(0.0, 1.0)
        fortune = random.uniform(5.0, 9.0)
    elif biome is Biome.DESERT:
        wealth = random.uniform(5.0, 9.0)
        harvest = random.uniform(0.0, 1.0)
        zeal = random.uniform(3.0, 6.0)
        fortune = random.uniform(1.0, 4.0)
    elif biome is Biome.MOUNTAIN:
        wealth = random.uniform(3.0, 6.0)
        harvest = random.uniform(1.0, 4.0)
        zeal = random.uniform(5.0, 9.0)
        fortune = random.uniform(0.0, 2.0)

    return wealth, harvest, zeal, fortune


def clamp(number: int, min_val: int, max_val: int) -> int:
    return max(min(max_val, number), min_val)


def attack(attacker: typing.Union[Unit, Heathen], defender: typing.Union[Unit, Heathen]) -> AttackData:
    attacker_dmg = attacker.plan.power * 0.25 * 1.2
    defender_dmg = defender.plan.power * 0.25
    defender.health -= attacker_dmg
    attacker.health -= defender_dmg
    attacker.has_attacked = True
    return AttackData(attacker, defender, defender_dmg, attacker_dmg, isinstance(attacker, Unit),
                      attacker.health < 0, defender.health < 0)


def get_player_totals(player: Player) -> (float, float, float, float):
    overall_harvest = 0
    overall_wealth = 0
    overall_zeal = 0
    overall_fortune = 0
    
    for setl in player.settlements:
        total_wealth = max(sum(quad.wealth for quad in setl.quads) +
                           sum(imp.effect.wealth for imp in setl.improvements), 0)
        total_wealth += (setl.level - 1) * 0.25 * total_wealth
        if setl.economic_status is EconomicStatus.RECESSION:
            total_wealth = 0
        elif setl.economic_status is EconomicStatus.BOOM:
            total_wealth *= 1.5
        total_wealth = round(total_wealth)
        total_harvest = max(sum(quad.harvest for quad in setl.quads) +
                            sum(imp.effect.harvest for imp in setl.improvements), 0)
        total_harvest += (setl.level - 1) * 0.25 * total_harvest
        if setl.harvest_status is HarvestStatus.POOR:
            total_harvest = 0
        elif setl.harvest_status is HarvestStatus.PLENTIFUL:
            total_harvest *= 1.5
        total_harvest = round(total_harvest)
        total_zeal = max(sum(quad.zeal for quad in setl.quads) +
                         sum(imp.effect.zeal for imp in setl.improvements), 0)
        total_zeal += (setl.level - 1) * 0.25 * total_zeal
        total_zeal = round(total_zeal)
        total_fortune = max(sum(quad.fortune for quad in setl.quads) +
                            sum(imp.effect.fortune for imp in setl.improvements), 0)
        total_fortune += (setl.level - 1) * 0.25 * total_fortune
        total_fortune = round(total_fortune)

        overall_harvest += total_harvest
        overall_wealth += total_wealth
        overall_zeal += total_zeal
        overall_fortune += total_fortune

    return overall_wealth, overall_harvest, overall_zeal, overall_fortune
