import random
from copy import deepcopy

from models import Biome, Unit, Heathen, AttackData, Player, EconomicStatus, HarvestStatus, Settlement, Improvement, \
    UnitPlan, SetlAttackData, GameConfig, InvestigationResult, Faction, Project, ProjectType


def calculate_yield_for_quad(biome: Biome) -> (float, float, float, float):
    """
    Given the supplied biome, generate a random yield to be used for a quad.
    :param biome: The biome of the quad-to-be.
    :return: A tuple of wealth, harvest, zeal, and fortune.
    """
    wealth: float = 0
    harvest: float = 0
    zeal: float = 0
    fortune: float = 0

    match biome:
        case Biome.FOREST:
            wealth = random.uniform(0.0, 2.0)
            harvest = random.uniform(5.0, 9.0)
            zeal = random.uniform(1.0, 4.0)
            fortune = random.uniform(3.0, 6.0)
        case Biome.SEA:
            wealth = random.uniform(1.0, 4.0)
            harvest = random.uniform(3.0, 6.0)
            zeal = random.uniform(0.0, 1.0)
            fortune = random.uniform(5.0, 9.0)
        case Biome.DESERT:
            wealth = random.uniform(5.0, 9.0)
            harvest = random.uniform(0.0, 1.0)
            zeal = random.uniform(3.0, 6.0)
            fortune = random.uniform(1.0, 4.0)
        case Biome.MOUNTAIN:
            wealth = random.uniform(3.0, 6.0)
            harvest = random.uniform(1.0, 4.0)
            zeal = random.uniform(5.0, 9.0)
            fortune = random.uniform(0.0, 2.0)

    return wealth, harvest, zeal, fortune


def clamp(number: int, min_val: int, max_val: int) -> int:
    """
    Clamp the supplied number to the supplied minimum and maximum values.
    :param number: The number to clamp.
    :param min_val: The minimum value.
    :param max_val: The maximum value.
    :return: The clamped number.
    """
    return max(min(max_val, number), min_val)


def attack(attacker: Unit | Heathen, defender: Unit | Heathen, ai=True) -> AttackData:
    """
    Execute an attack between the two supplied units.
    :param attacker: The unit initiating the attack.
    :param defender: The unit defending the attack.
    :param ai: Whether the attack was by an AI player.
    :return: An AttackData object summarising the results of the attack.
    """
    # Attackers get a damage bonus.
    attacker_dmg = attacker.plan.power * 0.25 * 1.2
    defender_dmg = defender.plan.power * 0.25
    defender.health -= attacker_dmg
    attacker.health -= defender_dmg
    attacker.has_attacked = True
    return AttackData(attacker, defender, defender_dmg, attacker_dmg, not ai,
                      attacker.health <= 0, defender.health <= 0)


def attack_setl(attacker: Unit, setl: Settlement, setl_owner: Player, ai=True) -> SetlAttackData:
    """
    Execute an attack by the supplied unit on the supplied settlement.
    :param attacker: The unit initiating the attack.
    :param setl: The settlement being attacked.
    :param setl_owner: The owner of the settlement under attack.
    :param ai: Whether the attack was by an AI player.
    :return: A SetlAttackData object summarising the results of the attack.
    """
    # Naturally, attacking units do a fraction of their usual damage to settlements. Conversely, settlements do
    # significantly more damage to units in comparison to another unit.
    attacker_dmg = attacker.plan.power * 0.1
    setl_dmg = setl.strength / 2
    attacker.health -= setl_dmg
    setl.strength = max(0.0, setl.strength - attacker_dmg)
    attacker.has_attacked = True
    return SetlAttackData(attacker, setl, setl_owner, setl_dmg, attacker_dmg, not ai,
                          attacker.health <= 0, setl.strength <= 0)


def get_player_totals(player: Player, is_night: bool) -> (float, float, float, float):
    """
    Get the wealth, harvest, zeal, and fortune totals for the given player.
    :param player: The player to calculate totals for.
    :param is_night: Whether it is night.
    :return: A tuple containing the player's wealth, harvest, zeal, and fortune.
    """
    overall_wealth = 0
    overall_harvest = 0
    overall_zeal = 0
    overall_fortune = 0

    # Just add together the stats for each of the player's settlements.
    for setl in player.settlements:
        setl_totals = get_setl_totals(player, setl, is_night)

        overall_wealth += setl_totals[0]
        overall_harvest += setl_totals[1]
        overall_zeal += setl_totals[2]
        overall_fortune += setl_totals[3]

    return overall_wealth, overall_harvest, overall_zeal, overall_fortune


def get_setl_totals(player: Player,
                    setl: Settlement,
                    is_night: bool,
                    strict: bool = False) -> (float, float, float, float):
    """
    Get the wealth, harvest, zeal, and fortune totals for the given Settlement.
    :param player: The owner of the settlement.
    :param setl: The settlement to calculate totals for.
    :param is_night: Whether it is night. Used as harvest is halved and fortune increased by 10% at night.
    :param strict: Whether the total should be 0 as opposed to 0.5 in situations where the total would be negative.
    Only used for the settlement overlay, as we want users to make progress even if their zeal/fortune is 0.
    :return: A tuple containing the settlement's wealth, harvest, zeal, and fortune.
    """

    # For each of the four categories, add together the values for all of the settlement's quads and improvements. If
    # negative, return 0 for wealth and harvest, and 0.5 for zeal and fortune. Also, use the settlement's level to add
    # to each of the four categories. For example, a level 5 settlement with 10 total wealth will have its wealth
    # doubled to 20. Similarly, a level 10 settlement with 10 total wealth will have its wealth increased to 32.5. Also
    # note that wealth and harvest are special because they have additional conditions applied relating to the
    # satisfaction of the settlement. Essentially, settlements with low satisfaction will yield no wealth/harvest, and
    # settlements with high satisfaction will yield 1.5 times the wealth and harvest.

    total_zeal = max(sum(quad.zeal for quad in setl.quads) +
                     sum(imp.effect.zeal for imp in setl.improvements), 0 if strict else 0.5)
    total_zeal += (setl.level - 1) * 0.25 * total_zeal
    if player.faction is Faction.AGRICULTURISTS:
        total_zeal *= 0.75
    elif player.faction is Faction.FUNDAMENTALISTS:
        total_zeal *= 1.25
    total_wealth = max(sum(quad.wealth for quad in setl.quads) +
                       sum(imp.effect.wealth for imp in setl.improvements), 0)
    total_wealth += (setl.level - 1) * 0.25 * total_wealth
    if setl.current_work is not None and isinstance(setl.current_work.construction, Project) and \
            setl.current_work.construction.type is ProjectType.ECONOMICAL:
        total_wealth += total_zeal / 4
    if setl.economic_status is EconomicStatus.RECESSION:
        total_wealth = 0
    elif setl.economic_status is EconomicStatus.BOOM:
        total_wealth *= 1.5
    if player.faction is Faction.GODLESS:
        total_wealth *= 1.25
    elif player.faction is Faction.ORTHODOX:
        total_wealth *= 0.75
    total_harvest = max(sum(quad.harvest for quad in setl.quads) +
                        sum(imp.effect.harvest for imp in setl.improvements), 0)
    total_harvest += (setl.level - 1) * 0.25 * total_harvest
    if setl.current_work is not None and isinstance(setl.current_work.construction, Project) and \
            setl.current_work.construction.type is ProjectType.BOUNTIFUL:
        total_harvest += total_zeal / 4
    if setl.harvest_status is HarvestStatus.POOR or setl.under_siege_by is not None:
        total_harvest = 0
    elif setl.harvest_status is HarvestStatus.PLENTIFUL:
        total_harvest *= 1.5
    if player.faction is Faction.RAVENOUS:
        total_harvest *= 1.25
    if is_night and player.faction is not Faction.NOCTURNE:
        total_harvest /= 2
    total_fortune = max(sum(quad.fortune for quad in setl.quads) +
                        sum(imp.effect.fortune for imp in setl.improvements), 0 if strict else 0.5)
    total_fortune += (setl.level - 1) * 0.25 * total_fortune
    if setl.current_work is not None and isinstance(setl.current_work.construction, Project) and \
            setl.current_work.construction.type is ProjectType.MAGICAL:
        total_fortune += total_zeal / 4
    if is_night:
        total_fortune *= 1.1
    if player.faction is Faction.SCRUTINEERS:
        total_fortune *= 0.75
    elif player.faction is Faction.ORTHODOX:
        total_fortune *= 1.25

    return total_wealth, total_harvest, total_zeal, total_fortune


def complete_construction(setl: Settlement, player: Player):
    """
    Completes the current construction for the given settlement.
    :param setl: The settlement having its construction completed.
    :param player: The owner of the settlement.
    """
    # If an improvement is being completed, add it to the settlement, and adjust the settlement's strength and
    # satisfaction.
    if isinstance(setl.current_work.construction, Improvement):
        setl.improvements.append(setl.current_work.construction)
        if setl.current_work.construction.effect.strength > 0:
            strength_multiplier = 2 if player.faction is Faction.CONCENTRATED else 1
            setl.strength += setl.current_work.construction.effect.strength * strength_multiplier
            setl.max_strength += setl.current_work.construction.effect.strength * strength_multiplier
        if setl.current_work.construction.effect.satisfaction != 0:
            setl.satisfaction += setl.current_work.construction.effect.satisfaction
            if setl.satisfaction < 0:
                setl.satisfaction = 0
            elif setl.satisfaction > 100:
                setl.satisfaction = 100
    # If a unit is being completed, add it to the garrison, and reduce the settlement's level if it was a settler.
    else:
        plan: UnitPlan = setl.current_work.construction
        if plan.can_settle:
            setl.level -= 1
            setl.harvest_reserves = pow(setl.level - 1, 2) * 25
            setl.produced_settler = True
        setl.garrison.append(Unit(plan.max_health, plan.total_stamina, setl.location, True, deepcopy(plan)))
    setl.current_work = None


def investigate_relic(player: Player, unit: Unit, relic_loc: (int, int), cfg: GameConfig) -> InvestigationResult:
    """
    Investigate a relic with the given unit.
    Possible rewards include:
    - Wealth bonus
    - Fortune bonus
    - Vision bonus (around the relic, only if fog of war enabled)
    - Permanent +5 health
    - Permanent +5 power
    - Permanent +1 stamina
    - Unit upkeep reduced to 0 permanently
    :param player: The owner of the unit investigating the relic.
    :param unit: The unit investigating the relic.
    :param relic_loc: The location of the relic.
    :param cfg: The game configuration, used to determine whether to grant vision bonuses, which are useless when fog of
    war is disabled.
    :return: The type of investigation result, i.e. the bonus granted, if there is one.
    """
    random_chance = random.randint(0, 100)
    # Scrutineers always succeed when investigating.
    was_successful = True if player.faction is Faction.SCRUTINEERS else random_chance < 70
    if was_successful:
        if random_chance < 10 and player.ongoing_blessing is not None:
            player.ongoing_blessing.fortune_consumed += player.ongoing_blessing.blessing.cost / 5
            return InvestigationResult.FORTUNE
        if random_chance < 20 or random_chance < 30 and not cfg.fog_of_war:
            player.wealth += 25
            return InvestigationResult.WEALTH
        if random_chance < 30 and cfg.fog_of_war:
            for i in range(relic_loc[1] - 10, relic_loc[1] + 11):
                for j in range(relic_loc[0] - 10, relic_loc[0] + 11):
                    player.quads_seen.add((j, i))
            return InvestigationResult.VISION
        if random_chance < 40:
            unit.plan.max_health += 5
            unit.health += 5
            return InvestigationResult.HEALTH
        if random_chance < 50:
            unit.plan.power += 5
            return InvestigationResult.POWER
        if random_chance < 60:
            unit.plan.total_stamina += 1
            unit.remaining_stamina = unit.plan.total_stamina
            return InvestigationResult.STAMINA
        unit.plan.cost = 0
        return InvestigationResult.UPKEEP
    return InvestigationResult.NONE
