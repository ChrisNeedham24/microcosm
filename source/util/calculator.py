import random
from copy import deepcopy
from typing import List, Tuple, Set, Generator, Optional

from source.foundation.models import Biome, Unit, Heathen, AttackData, Player, EconomicStatus, HarvestStatus, \
    Settlement, Improvement, UnitPlan, SetlAttackData, GameConfig, InvestigationResult, Faction, Project, ProjectType, \
    HealData, DeployerUnitPlan, DeployerUnit, ResourceCollection, Quad, Blessing


def calculate_yield_for_quad(biome: Biome) -> Tuple[int, int, int, int]:
    """
    Given the supplied biome, generate a random yield to be used for a quad.
    :param biome: The biome of the quad-to-be.
    :return: A tuple of wealth, harvest, zeal, and fortune.
    """
    wealth: int = 0
    harvest: int = 0
    zeal: int = 0
    fortune: int = 0

    match biome:
        case Biome.FOREST:
            wealth = random.randint(0, 2)
            harvest = random.randint(5, 9)
            zeal = random.randint(1, 4)
            fortune = random.randint(3, 6)
        case Biome.SEA:
            wealth = random.randint(1, 4)
            harvest = random.randint(3, 6)
            zeal = random.randint(0, 1)
            fortune = random.randint(5, 9)
        case Biome.DESERT:
            wealth = random.randint(5, 9)
            harvest = random.randint(0, 1)
            zeal = random.randint(3, 6)
            fortune = random.randint(1, 4)
        case Biome.MOUNTAIN:
            wealth = random.randint(3, 6)
            harvest = random.randint(1, 4)
            zeal = random.randint(5, 9)
            fortune = random.randint(0, 2)

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
    attacker.has_acted = True
    return AttackData(attacker, defender, defender_dmg, attacker_dmg, not ai,
                      attacker.health <= 0, defender.health <= 0)


def heal(healer: Unit, healed: Unit, ai=True) -> HealData:
    """
    Execute a healing action between the two supplied units.
    :param healer: The unit healing the other.
    :param healed: The unit being healed.
    :param ai: Whether the healing action was by an AI player.
    :return: A HealData object summarising the results of the healing action.
    """
    original_health = healed.health
    healed.health = min(healed.health + healer.plan.power, healed.plan.max_health)
    healer.has_acted = True
    return HealData(healer, healed, healer.plan.power, original_health, not ai)


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
    attacker.has_acted = True
    return SetlAttackData(attacker, setl, setl_owner, setl_dmg, attacker_dmg, not ai,
                          attacker.health <= 0, setl.strength <= 0)


def get_player_totals(player: Player, is_night: bool) -> Tuple[float, float, float, float]:
    """
    Get the wealth, harvest, zeal, and fortune totals for the given player.
    :param player: The player to calculate totals for.
    :param is_night: Whether it is night.
    :return: A tuple containing the player's wealth, harvest, zeal, and fortune.
    """
    overall_wealth: float = 0.0
    overall_harvest: float = 0.0
    overall_zeal: float = 0.0
    overall_fortune: float = 0.0

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
                    strict: bool = False) -> Tuple[float, float, float, float]:
    """
    Get the wealth, harvest, zeal, and fortune totals for the given Settlement.
    :param player: The owner of the settlement.
    :param setl: The settlement to calculate totals for.
    :param is_night: Whether it is night. Used as harvest is halved and fortune increased by 10% at night.
    :param strict: Whether the total should be 0 as opposed to 1 in situations where the total would be negative.
    Only used for the settlement overlay, as we want users to make progress even if their zeal/fortune is 0.
    :return: A tuple containing the settlement's wealth, harvest, zeal, and fortune.
    """

    # For each of the four categories, add together the values for all of the settlement's quads and improvements. If
    # negative, return 0 for wealth and harvest, and 1 for zeal and fortune. Also, use the settlement's level to add
    # to each of the four categories. For example, a level 5 settlement with 10 total wealth will have its wealth
    # doubled to 20. Similarly, a level 10 settlement with 10 total wealth will have its wealth increased to 32.5. Also
    # note that wealth and harvest are special because they have additional conditions applied relating to the
    # satisfaction of the settlement. Essentially, settlements with low satisfaction will yield no wealth/harvest, and
    # settlements with high satisfaction will yield 1.5 times the wealth and harvest.

    total_zeal: float = float(max(sum(quad.zeal for quad in setl.quads) +
                                  sum(imp.effect.zeal for imp in setl.improvements), 0 if strict else 1))
    total_zeal += (setl.level - 1) * 0.25 * total_zeal
    if player.faction == Faction.AGRICULTURISTS:
        total_zeal *= 0.75
    elif player.faction == Faction.FUNDAMENTALISTS:
        total_zeal *= 1.25
    total_wealth: float = float(max(sum(quad.wealth for quad in setl.quads) +
                                    sum(imp.effect.wealth for imp in setl.improvements), 0))
    total_wealth += (setl.level - 1) * 0.25 * total_wealth
    if setl.current_work is not None and isinstance(setl.current_work.construction, Project) and \
            setl.current_work.construction.type is ProjectType.ECONOMICAL:
        total_wealth += total_zeal / 4
    if setl.economic_status is EconomicStatus.RECESSION:
        total_wealth = 0.0
    elif setl.economic_status is EconomicStatus.BOOM:
        total_wealth *= 1.5
    if player.faction == Faction.GODLESS:
        total_wealth *= 1.25
    elif player.faction == Faction.ORTHODOX:
        total_wealth *= 0.75
    if setl.resources.aurora:
        total_wealth *= (1 + 0.5 * setl.resources.aurora)
    total_harvest: float = float(max(sum(quad.harvest for quad in setl.quads) +
                                     sum(imp.effect.harvest for imp in setl.improvements), 0))
    total_harvest += (setl.level - 1) * 0.25 * total_harvest
    if setl.current_work is not None and isinstance(setl.current_work.construction, Project) and \
            setl.current_work.construction.type is ProjectType.BOUNTIFUL:
        total_harvest += total_zeal / 4
    if setl.harvest_status is HarvestStatus.POOR or setl.besieged:
        total_harvest = 0.0
    elif setl.harvest_status is HarvestStatus.PLENTIFUL:
        total_harvest *= 1.5
    if player.faction == Faction.RAVENOUS:
        total_harvest *= 1.25
    if is_night and player.faction != Faction.NOCTURNE and not setl.resources.sunstone:
        total_harvest /= 2
    total_fortune: float = float(max(sum(quad.fortune for quad in setl.quads) +
                                     sum(imp.effect.fortune for imp in setl.improvements), 0 if strict else 1))
    total_fortune += (setl.level - 1) * 0.25 * total_fortune
    if setl.current_work is not None and isinstance(setl.current_work.construction, Project) and \
            setl.current_work.construction.type is ProjectType.MAGICAL:
        total_fortune += total_zeal / 4
    if is_night:
        total_fortune *= 1.1
    if player.faction == Faction.SCRUTINEERS:
        total_fortune *= 0.75
    elif player.faction == Faction.ORTHODOX:
        total_fortune *= 1.25
    if setl.resources.aquamarine:
        total_fortune *= (1 + 0.5 * setl.resources.aquamarine)

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
            strength_multiplier = 2 if player.faction == Faction.CONCENTRATED else 1
            setl.strength += setl.current_work.construction.effect.strength * strength_multiplier
            setl.max_strength += setl.current_work.construction.effect.strength * strength_multiplier
        if setl.current_work.construction.effect.satisfaction != 0:
            setl.satisfaction += setl.current_work.construction.effect.satisfaction
            if setl.satisfaction < 0:
                setl.satisfaction = 0.0
            elif setl.satisfaction > 100:
                setl.satisfaction = 100.0
    # If a unit is being completed, add it to the garrison, and reduce the settlement's level if it was a settler.
    else:
        plan: UnitPlan = setl.current_work.construction
        if plan.can_settle:
            setl.level -= 1
            setl.harvest_reserves = pow(setl.level - 1, 2) * 25.0
            setl.produced_settler = True
        if isinstance(plan, DeployerUnitPlan):
            setl.garrison.append(DeployerUnit(plan.max_health, plan.total_stamina, setl.location, True, deepcopy(plan)))
        else:
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
    - 10 ore, timber, or magma
    :param player: The owner of the unit investigating the relic.
    :param unit: The unit investigating the relic.
    :param relic_loc: The location of the relic.
    :param cfg: The game configuration, used to determine whether to grant vision bonuses, which are useless when fog of
    war is disabled.
    :return: The type of investigation result, i.e. the bonus granted, if there is one.
    """
    random_chance = random.randint(0, 140)
    # Scrutineers always succeed when investigating.
    was_successful = True if player.faction == Faction.SCRUTINEERS else random_chance < 100
    if was_successful:
        # For players of the Scrutineers faction, we need to scale down their random value, as if it was 100 or more,
        # then the result would always be the last investigation result.
        if player.faction == Faction.SCRUTINEERS:
            random_chance *= (100 / 140)
        if random_chance < 10 and player.ongoing_blessing is not None:
            player.ongoing_blessing.fortune_consumed += player.ongoing_blessing.blessing.cost / 5
            return InvestigationResult.FORTUNE
        if random_chance < 20 or random_chance < 30 and not cfg.fog_of_war:
            player.wealth += 25
            return InvestigationResult.WEALTH
        if random_chance < 30 and cfg.fog_of_war:
            update_player_quads_seen_around_point(player, relic_loc, vision_range=10)
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
        if random_chance < 70:
            unit.plan.cost = 0.0
            return InvestigationResult.UPKEEP
        if random_chance < 80:
            player.resources.ore += 10
            return InvestigationResult.ORE
        if random_chance < 90:
            player.resources.timber += 10
            return InvestigationResult.TIMBER
        player.resources.magma += 10
        return InvestigationResult.MAGMA
    return InvestigationResult.NONE


def gen_spiral_indices(initial_loc: (int, int)) -> List[Tuple[int, int]]:
    """
    Generate indices (or locations) around a supplied point in a spiral fashion. The below diagram indicates the order
    in which points should be returned.

    ----------------
    |20|21|22|23|24|
    ----------------
    |19|06|07|08|09|
    ----------------
    |18|05|XX|01|10|
    ----------------
    |17|04|03|02|11|
    ----------------
    |16|15|14|13|12|
    ----------------

    :param initial_loc: The point to 'spiral' around.
    :return: A list of locations, in the order of the spiral.
    """
    indices: List[Tuple[int, int]] = []

    x = 0
    y = 0
    delta = 1
    m = 1

    while m <= 5:
        while 2 * x * delta < m:
            indices.append((x + initial_loc[0], y + initial_loc[1]))
            x += delta
        while 2 * y * delta < m:
            indices.append((x + initial_loc[0], y + initial_loc[1]))
            y += delta
        delta *= -1
        m += 1

    return indices


def get_resources_for_settlement(setl_locs: List[Tuple[int, int]],
                                 quads: List[List[Quad]]) -> ResourceCollection:
    """
    Determine and return the resources that a settlement with the given locations would be able to exploit.
    :param setl_locs: The locations of the quads belonging to the settlement.
    :param quads: The quads on the board.
    :return: A ResourceCollection representation of the settlement's resources.
    """
    setl_resources: ResourceCollection = ResourceCollection()
    # We need to keep track of the quads that we've already seen so that settlements with multiple quads don't double up
    # resources from the same quad.
    found_locs: Set[Tuple[int, int]] = set()
    for setl_loc in setl_locs:
        for i in range(setl_loc[0] - 1, setl_loc[0] + 2):
            for j in range(setl_loc[1] - 1, setl_loc[1] + 2):
                if 0 <= i <= 99 and 0 <= j <= 89:
                    if quads[j][i].resource and (j, i) not in found_locs:
                        setl_resources.ore += quads[j][i].resource.ore
                        setl_resources.timber += quads[j][i].resource.timber
                        setl_resources.magma += quads[j][i].resource.magma
                        setl_resources.aurora += quads[j][i].resource.aurora
                        setl_resources.bloodstone += quads[j][i].resource.bloodstone
                        setl_resources.obsidian += quads[j][i].resource.obsidian
                        setl_resources.sunstone += quads[j][i].resource.sunstone
                        setl_resources.aquamarine += quads[j][i].resource.aquamarine
                        found_locs.add((j, i))
    return setl_resources


def player_has_resources_for_improvement(player: Player, improvement: Improvement) -> bool:
    """
    Return whether the given player has the resources (if required) to construct the given improvement.
    :param player: The player checking whether they can construct the given improvement.
    :param improvement: The improvement being validated against the given player.
    :return: Whether the player can construct the improvement.
    """
    return not improvement.req_resources or (player.resources.ore >= improvement.req_resources.ore and
                                             player.resources.timber >= improvement.req_resources.timber and
                                             player.resources.magma >= improvement.req_resources.magma)


def subtract_player_resources_for_improvement(player: Player, improvement: Improvement):
    """
    Deduct the required resources for the given improvement from the given player's resources.
    :param player: The player having their resources deducted.
    :param improvement: The improvement being constructed.
    """
    player.resources.ore -= improvement.req_resources.ore
    player.resources.timber -= improvement.req_resources.timber
    player.resources.magma -= improvement.req_resources.magma


def split_list_into_chunks(list_to_split: list, chunk_length: int) -> Generator[list, None, None]:
    """
    Splits a list into chunks of a given size.
    Once the Python version for Microcosm is upgraded to 3.12, itertools.batched() can be used instead of this.
    :param list_to_split: The list to generate chunks from.
    :param chunk_length: The size of each chunk to return.
    :return: A generator that yields chunks of the given list with the given size.
    """
    for i in range(0, len(list_to_split), chunk_length):
        yield list_to_split[i:i + chunk_length]


def update_player_quads_seen_around_point(player: Player, point: (int, int), vision_range: int = 5):
    """
    Updates the seen quads for a player around the given point with the given range.
    :param player: The player to update the seen quads for.
    :param point: The point around which seen quads are to be added.
    :param vision_range: The 'distance' from the point to add seen quads for.
    """
    for i in range(point[1] - vision_range, point[1] + vision_range + 1):
        for j in range(point[0] - vision_range, point[0] + vision_range + 1):
            player.quads_seen.add((clamp(j, 0, 99), clamp(i, 0, 89)))


def scale_unit_plan_attributes(unit_plan: UnitPlan,
                               faction: Faction,
                               setl_resources: Optional[ResourceCollection]) -> UnitPlan:
    """
    Scale the attributes of the given unit plan, based on the supplied faction and, optionally, the resources of the
    settlement they're being constructed in.
    :param unit_plan: The unit plan to scale the attributes for.
    :param faction: The faction the unit plan belongs to.
    :param setl_resources: The optionally-supplied resource collection of the settlement that this unit plan will be
                           constructed in. Naturally unsupplied if the unit plan is not under construction.
    :return: The supplied unit plan, with scaled attributes if necessary.
    """
    match faction:
        case Faction.IMPERIALS:
            unit_plan.power *= 1.5
        case Faction.PERSISTENT:
            unit_plan.max_health *= 1.5
            unit_plan.power *= 0.75
        case Faction.EXPLORERS:
            unit_plan.total_stamina = round(1.5 * unit_plan.total_stamina)
            unit_plan.max_health *= 0.75

    if setl_resources is not None and setl_resources.bloodstone:
        unit_plan.power *= (1 + 0.5 * setl_resources.bloodstone)
        unit_plan.max_health *= (1 + 0.5 * setl_resources.bloodstone)

    return unit_plan


def scale_blessing_attributes(blessing: Blessing, faction: Faction) -> Blessing:
    """
    Scale the attributes of the given blessing, based on the supplied faction.
    :param blessing: The blessing to scale the attributes for.
    :param faction: The faction the blessing belongs to.
    :return: The supplied blessing, with scaled attributes if necessary.
    """
    if faction == Faction.GODLESS:
        blessing.cost *= 1.5
    return blessing
