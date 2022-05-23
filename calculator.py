import random
import typing

from models import Biome, Unit, Heathen, AttackData, Player, EconomicStatus, HarvestStatus, Settlement, Improvement, \
    UnitPlan, SetlAttackData


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


def attack(attacker: typing.Union[Unit, Heathen], defender: typing.Union[Unit, Heathen], ai=True) -> AttackData:
    attacker_dmg = attacker.plan.power * 0.25 * 1.2
    defender_dmg = defender.plan.power * 0.25
    defender.health -= attacker_dmg
    attacker.health -= defender_dmg
    attacker.has_attacked = True
    return AttackData(attacker, defender, defender_dmg, attacker_dmg, not ai, attacker.health <= 0, defender.health <= 0)


def attack_setl(attacker: Unit, setl: Settlement, setl_owner: Player, ai=True) -> SetlAttackData:
    attacker_dmg = attacker.plan.power * 0.1
    setl_dmg = setl.strength / 2
    attacker.health -= setl_dmg
    setl.strength -= attacker_dmg
    attacker.has_attacked = True
    return SetlAttackData(attacker, setl, setl_owner, setl_dmg, attacker_dmg, not ai,
                          attacker.health <= 0, setl.strength <= 0)


def get_player_totals(player: Player) -> (float, float, float, float):
    overall_harvest = 0
    overall_wealth = 0
    overall_zeal = 0
    overall_fortune = 0
    
    for setl in player.settlements:
        setl_totals = get_setl_totals(setl)

        overall_harvest += setl_totals[0]
        overall_wealth += setl_totals[1]
        overall_zeal += setl_totals[2]
        overall_fortune += setl_totals[3]

    return overall_wealth, overall_harvest, overall_zeal, overall_fortune


def get_setl_totals(setl: Settlement, strict: bool = False) -> (float, float, float, float):
    total_wealth = max(sum(quad.wealth for quad in setl.quads) +
                       sum(imp.effect.wealth for imp in setl.improvements), 0)
    total_wealth += (setl.level - 1) * 0.25 * total_wealth
    if setl.economic_status is EconomicStatus.RECESSION:
        total_wealth = 0
    elif setl.economic_status is EconomicStatus.BOOM:
        total_wealth *= 1.5
    total_harvest = max(sum(quad.harvest for quad in setl.quads) +
                        sum(imp.effect.harvest for imp in setl.improvements), 0)
    total_harvest += (setl.level - 1) * 0.25 * total_harvest
    if setl.harvest_status is HarvestStatus.POOR or setl.under_siege_by is not None:
        total_harvest = 0
    elif setl.harvest_status is HarvestStatus.PLENTIFUL:
        total_harvest *= 1.5
    total_zeal = max(sum(quad.zeal for quad in setl.quads) +
                     sum(imp.effect.zeal for imp in setl.improvements), 0 if strict else 0.5)
    total_zeal += (setl.level - 1) * 0.25 * total_zeal
    total_fortune = max(sum(quad.fortune for quad in setl.quads) +
                        sum(imp.effect.fortune for imp in setl.improvements), 0 if strict else 0.5)
    total_fortune += (setl.level - 1) * 0.25 * total_fortune

    return total_wealth, total_harvest, total_zeal, total_fortune


def complete_construction(setl: Settlement):
    if isinstance(setl.current_work.construction, Improvement):
        setl.improvements.append(setl.current_work.construction)
        if setl.current_work.construction.effect.strength > 0:
            setl.strength += setl.current_work.construction.effect.strength
            setl.max_strength += setl.current_work.construction.effect.strength
        if setl.current_work.construction.effect.satisfaction != 0:
            setl.satisfaction += setl.current_work.construction.effect.satisfaction
            if setl.satisfaction < 0:
                setl.satisfaction = 0
            elif setl.satisfaction > 100:
                setl.satisfaction = 100
    else:
        plan: UnitPlan = setl.current_work.construction
        if plan.can_settle:
            setl.level -= 1
            setl.harvest_reserves = pow(setl.level - 1, 2) * 25
            setl.produced_settler = True
        setl.garrison.append(Unit(plan.max_health, plan.total_stamina, setl.location, True, plan))
    setl.current_work = None
