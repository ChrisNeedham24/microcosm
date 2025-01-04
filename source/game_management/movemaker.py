import operator
import random
from typing import List, Tuple, Optional

from source.util.calculator import get_player_totals, get_setl_totals, attack, complete_construction, clamp, \
    attack_setl, investigate_relic, heal, gen_spiral_indices, get_resources_for_settlement, \
    subtract_player_resources_for_improvement, update_player_quads_seen_around_point
from source.foundation.catalogue import get_available_blessings, get_unlockable_improvements, get_unlockable_units, \
    get_available_improvements, get_available_unit_plans, Namer
from source.foundation.models import Player, Blessing, AttackPlaystyle, OngoingBlessing, Settlement, Improvement, \
    UnitPlan, Construction, Unit, ExpansionPlaystyle, Quad, GameConfig, Faction, VictoryType, DeployerUnitPlan, \
    DeployerUnit, Project, ResourceCollection


def set_blessing(player: Player, player_totals: (float, float, float, float)):
    """
    Choose and begin undergoing a blessing for the given AI player.
    :param player: The AI player having its blessing chosen.
    :param player_totals: The current totals for the AI player (wealth, harvest, zeal, fortune).
    """
    avail_bless = get_available_blessings(player)
    if len(avail_bless) > 0:
        ideal: Blessing = avail_bless[0]
        # The 'ideal' blessing is determined by finding the blessing that boosts the category the AI player is most
        # lacking in.
        match player_totals.index(min(player_totals)):
            case 0:
                highest_wealth: Tuple[float, Blessing] = 0, avail_bless[0]
                for bless in avail_bless:
                    cumulative_wealth: float = 0
                    for imp in get_unlockable_improvements(bless):
                        cumulative_wealth += imp.effect.wealth
                    if cumulative_wealth > highest_wealth[0]:
                        highest_wealth = cumulative_wealth, bless
                ideal = highest_wealth[1]
            case 1:
                highest_harvest: Tuple[float, Blessing] = 0, avail_bless[0]
                for bless in avail_bless:
                    cumulative_harvest: float = 0
                    for imp in get_unlockable_improvements(bless):
                        cumulative_harvest += imp.effect.harvest
                    if cumulative_harvest > highest_harvest[0]:
                        highest_harvest = cumulative_harvest, bless
                ideal = highest_harvest[1]
            case 2:
                highest_zeal: Tuple[float, Blessing] = 0, avail_bless[0]
                for bless in avail_bless:
                    cumulative_zeal: float = 0
                    for imp in get_unlockable_improvements(bless):
                        cumulative_zeal += imp.effect.zeal
                    if cumulative_zeal > highest_zeal[0]:
                        highest_zeal = cumulative_zeal, bless
                ideal = highest_zeal[1]
            case 3:
                highest_fortune: Tuple[float, Blessing] = 0, avail_bless[0]
                for bless in avail_bless:
                    cumulative_fortune: float = 0
                    for imp in get_unlockable_improvements(bless):
                        cumulative_fortune += imp.effect.fortune
                    if cumulative_fortune > highest_fortune[0]:
                        highest_fortune = cumulative_fortune, bless
                ideal = highest_fortune[1]
        # Aggressive AIs will choose the first blessing that unlocks a unit, if there is one. If there aren't any, they
        # will undergo the 'ideal' blessing.
        match player.ai_playstyle.attacking:
            case AttackPlaystyle.AGGRESSIVE:
                for bless in avail_bless:
                    unlockable = get_unlockable_units(bless)
                    if len(unlockable) > 0:
                        player.ongoing_blessing = OngoingBlessing(bless)
                        break
                if player.ongoing_blessing is None:
                    player.ongoing_blessing = OngoingBlessing(ideal)
            # Defensive AIs will choose the first blessing that unlocks an improvement that increases settlement
            # strength. If there aren't any, they will undergo the 'ideal' blessing.
            case AttackPlaystyle.DEFENSIVE:
                for bless in avail_bless:
                    unlockable = get_unlockable_improvements(bless)
                    if len([imp for imp in unlockable if imp.effect.strength > 0]) > 0:
                        player.ongoing_blessing = OngoingBlessing(bless)
                        break
                if player.ongoing_blessing is None:
                    player.ongoing_blessing = OngoingBlessing(ideal)
            # Neutral AIs will always choose the 'ideal' blessing.
            case _:
                player.ongoing_blessing = OngoingBlessing(ideal)


def set_player_construction(player: Player, setl: Settlement, is_night: bool):
    """
    Choose and begin a construction for the player's settlement. Note that this function is adapted from the below
    set_ai_construction() function.
    :param player: The non-AI player.
    :param setl: The settlement having its construction chosen.
    :param is_night: Whether it is night.
    """

    avail_imps = get_available_improvements(player, setl, strict=True)
    avail_units = get_available_unit_plans(player, setl)
    # Note that if there are no available improvements for the given settlement, the 'ideal' construction will default
    # to the first available unit. Additionally, the first improvement is only selected if it won't reduce satisfaction.
    ideal: Improvement | UnitPlan = avail_imps[0] \
        if len(avail_imps) > 0 and setl.satisfaction + avail_imps[0].effect.satisfaction >= 50 \
        else avail_units[0]
    totals = get_setl_totals(player, setl, is_night)

    # If the player has neither units on the board nor garrisoned, construct the first available.
    if len(player.units) == 0 and len(setl.garrison) == 0:
        setl.current_work = Construction(avail_units[0])
    else:
        if len(avail_imps) > 0:
            # The 'ideal' construction in all other cases is the one that will yield the effect that boosts the
            # category the settlement is most lacking in, and doesn't reduce satisfaction below 50.
            match totals.index(min(totals)):
                case 0:
                    highest_wealth: (float, Improvement) = avail_imps[0].effect.wealth, avail_imps[0]
                    for imp in avail_imps:
                        if imp.effect.wealth > highest_wealth[0] and setl.satisfaction + imp.effect.satisfaction >= 50:
                            highest_wealth = imp.effect.wealth, imp
                    ideal = highest_wealth[1]
                case 1:
                    highest_harvest: (float, Improvement) = avail_imps[0].effect.harvest, avail_imps[0]
                    for imp in avail_imps:
                        if imp.effect.harvest > highest_harvest[0] and \
                                setl.satisfaction + imp.effect.satisfaction >= 50:
                            highest_harvest = imp.effect.harvest, imp
                    ideal = highest_harvest[1]
                case 2:
                    highest_zeal: (float, Improvement) = avail_imps[0].effect.zeal, avail_imps[0]
                    for imp in avail_imps:
                        if imp.effect.zeal > highest_zeal[0] and setl.satisfaction + imp.effect.satisfaction >= 50:
                            highest_zeal = imp.effect.zeal, imp
                    ideal = highest_zeal[1]
                case 3:
                    highest_fortune: (float, Improvement) = avail_imps[0].effect.fortune, avail_imps[0]
                    for imp in avail_imps:
                        if imp.effect.fortune > highest_fortune[0] and \
                                setl.satisfaction + imp.effect.satisfaction >= 50:
                            highest_fortune = imp.effect.fortune, imp
                    ideal = highest_fortune[1]

        sat_imps = [imp for imp in avail_imps if imp.effect.satisfaction > 0]
        harv_imps = [imp for imp in avail_imps if imp.effect.harvest > 0]
        # If the settlement is dissatisfied, the easiest way to increase satisfaction is by constructing improvements
        # that either directly increase satisfaction, or by indirectly increasing satisfaction through increasing
        # harvest, which contributes to settlement satisfaction.
        if setl.satisfaction < 50 and (sat_imps or harv_imps):
            # The improvement with the lowest cost and the highest combined satisfaction and harvest is chosen.
            imps = sat_imps + harv_imps
            # Combined benefit, cost, Improvement.
            most_beneficial: Tuple[float, float, Improvement] = \
                imps[0].effect.satisfaction + imps[0].effect.harvest, imps[0].cost, imps[0]
            for i in imps:
                # Pick the improvement that yields the highest combined benefit while also not costing more than the
                # current ideal one. We do this to stop improvements being selected that will take 50 turns to
                # construct, all the while, the satisfaction is decreasing.
                if benefit := (i.effect.satisfaction + i.effect.harvest) > most_beneficial[0] and \
                              i.cost <= most_beneficial[1]:
                    most_beneficial = benefit, i.cost, i
            # Even still, if the improvement will take a long time relative to other non-harvest/satisfaction
            # improvements, just do the ideal instead.
            if avail_imps[0].cost * 5 < most_beneficial[1]:
                setl.current_work = Construction(ideal)
            else:
                setl.current_work = Construction(most_beneficial[2])
        # Alternatively, if we are below the benchmark for harvest for this settlement (i.e. the harvest is low enough
        # that it is decreasing satisfaction), try to construct an improvement that will increase it.
        elif totals[1] < setl.level * 4 and harv_imps:
            most_harvest: (int, float, Improvement) = harv_imps[0].effect.harvest, harv_imps[0].cost, harv_imps[0]
            for i in harv_imps:
                if i.effect.harvest > most_harvest[0] and i.cost <= most_harvest[1]:
                    most_harvest = i.effect.harvest, i.cost, i
            setl.current_work = Construction(most_harvest[2])
        # In all other circumstances, i.e. most of the time, just construct the ideal improvement.
        else:
            setl.current_work = Construction(ideal)
    # If the selected construction ended up being an improvement that requires resources, subtract those from the
    # player's total.
    if isinstance(cons := setl.current_work.construction, Improvement) and cons.req_resources:
        subtract_player_resources_for_improvement(player, cons)


def set_ai_construction(player: Player, setl: Settlement, is_night: bool,
                        other_player_vics: List[Tuple[Player, int]]):
    """
    Choose and begin a construction for the given AI player's settlement.
    :param player: The AI owner of the given settlement.
    :param setl: The settlement having its construction chosen.
    :param is_night: Whether it is night.
    :param other_player_vics: A list of tuples of players and the number of imminent victories they have. Note that
    players without any imminent victories are not included in this list.
    """

    def get_expansion_lvl() -> int:
        """
        Returns the settlement level at which an AI player will construct a settler unit to found a new settlement.
        :return: The required level for a new settlement.
        """
        if player.ai_playstyle.expansion == ExpansionPlaystyle.EXPANSIONIST:
            return 3
        if player.ai_playstyle.expansion == ExpansionPlaystyle.NEUTRAL:
            return 5
        return 10

    avail_imps = get_available_improvements(player, setl, strict=True)
    avail_units = get_available_unit_plans(player, setl)
    settler_units = [settler for settler in avail_units if settler.can_settle]
    healer_units = [healer for healer in avail_units if healer.heals]
    deployer_units = [deployer for deployer in avail_units if isinstance(deployer, DeployerUnitPlan)]
    # Note that if there are no available improvements for the given settlement, the 'ideal' construction will default
    # to the first available unit. Additionally, the first improvement is only selected if it won't reduce satisfaction.
    ideal: Improvement | UnitPlan = avail_imps[0] \
        if len(avail_imps) > 0 and setl.satisfaction + avail_imps[0].effect.satisfaction >= 50 \
        else avail_units[0]
    totals = get_setl_totals(player, setl, is_night)

    # If the AI player has neither units on the board nor garrisoned, construct the first available.
    if len(player.units) == 0 and len(setl.garrison) == 0:
        setl.current_work = Construction(avail_units[0])
    # If the settlement has not yet produced a settler in its 'lifetime', and it has now reached its required level for
    # expansion, choose that. Alternatively, if the AI is facing a situation where all of their settlements are
    # dissatisfied, and they can produce a settler, produce one regardless of whether they have produced one before.
    # Naturally, The Concentrated are exempt from this requirement.
    elif player.faction != Faction.CONCENTRATED and \
            ((setl.level >= get_expansion_lvl() and not setl.produced_settler) or
             (setl.level > 1 and all(setl.satisfaction < 40 for setl in player.settlements))):
        setl.current_work = Construction(settler_units[0])
    else:
        if len(avail_imps) > 0:
            # The 'ideal' construction in all other cases is the one that will yield the effect that boosts the
            # category the settlement is most lacking in, and doesn't reduce satisfaction below 50.
            match totals.index(min(totals)):
                case 0:
                    highest_wealth: (float, Improvement) = avail_imps[0].effect.wealth, avail_imps[0]
                    for imp in avail_imps:
                        if imp.effect.wealth > highest_wealth[0] and setl.satisfaction + imp.effect.satisfaction >= 50:
                            highest_wealth = imp.effect.wealth, imp
                    ideal = highest_wealth[1]
                case 1:
                    highest_harvest: (float, Improvement) = avail_imps[0].effect.harvest, avail_imps[0]
                    for imp in avail_imps:
                        if imp.effect.harvest > highest_harvest[0] and \
                                setl.satisfaction + imp.effect.satisfaction >= 50:
                            highest_harvest = imp.effect.harvest, imp
                    ideal = highest_harvest[1]
                case 2:
                    highest_zeal: (float, Improvement) = avail_imps[0].effect.zeal, avail_imps[0]
                    for imp in avail_imps:
                        if imp.effect.zeal > highest_zeal[0] and setl.satisfaction + imp.effect.satisfaction >= 50:
                            highest_zeal = imp.effect.zeal, imp
                    ideal = highest_zeal[1]
                case 3:
                    highest_fortune: (float, Improvement) = avail_imps[0].effect.fortune, avail_imps[0]
                    for imp in avail_imps:
                        if imp.effect.fortune > highest_fortune[0] and \
                                setl.satisfaction + imp.effect.satisfaction >= 50:
                            highest_fortune = imp.effect.fortune, imp
                    ideal = highest_fortune[1]

        sat_imps = [imp for imp in avail_imps if imp.effect.satisfaction > 0]
        harv_imps = [imp for imp in avail_imps if imp.effect.harvest > 0]
        # If the settlement is dissatisfied, the easiest way to increase satisfaction is by constructing improvements
        # that either directly increase satisfaction, or by indirectly increasing satisfaction through increasing
        # harvest, which contributes to settlement satisfaction.
        if setl.satisfaction < 50 and (sat_imps or harv_imps):
            # The improvement with the lowest cost and the highest combined satisfaction and harvest is chosen.
            imps = sat_imps + harv_imps
            # Combined benefit, cost, Improvement.
            most_beneficial: Tuple[float, float, Improvement] = \
                imps[0].effect.satisfaction + imps[0].effect.harvest, imps[0].cost, imps[0]
            for i in imps:
                # Pick the improvement that yields the highest combined benefit while also not costing more than the
                # current ideal one. We do this to stop AIs choosing improvements that will take 50 turns to construct,
                # all the while, their satisfaction is decreasing.
                if benefit := (i.effect.satisfaction + i.effect.harvest) > most_beneficial[0] and \
                              i.cost <= most_beneficial[1]:
                    most_beneficial = benefit, i.cost, i
            # Even still, if the improvement will take a long time relative to other non-harvest/satisfaction
            # improvements, just do the ideal instead.
            if avail_imps[0].cost * 5 < most_beneficial[1]:
                setl.current_work = Construction(ideal)
            else:
                setl.current_work = Construction(most_beneficial[2])
        # Alternatively, if we are below the benchmark for harvest for this settlement (i.e. the harvest is low enough
        # that it is decreasing satisfaction), try to construct an improvement that will increase it.
        elif totals[1] < setl.level * 4 and harv_imps:
            most_harvest: (int, float, Improvement) = harv_imps[0].effect.harvest, harv_imps[0].cost, harv_imps[0]
            for i in harv_imps:
                if i.effect.harvest > most_harvest[0] and i.cost <= most_harvest[1]:
                    most_harvest = i.effect.harvest, i.cost, i
            setl.current_work = Construction(most_harvest[2])
        # Another situation that can occur is that another player is close to achieving a victory. In this case, if the
        # AI has undergone a blessing that grants it the ability to construct deployer units, and they don't have any
        # deployer units currently deployed that have capacity for more passengers, construct a deployer unit.
        elif other_player_vics and deployer_units and not \
                [u for u in player.units if isinstance(u, DeployerUnit) and len(u.passengers) < u.plan.max_capacity]:
            most_capacity: (int, UnitPlan) = deployer_units[0].max_capacity, deployer_units[0]
            for dep in deployer_units:
                if dep.max_capacity >= most_capacity[0]:
                    most_capacity = dep.max_capacity, dep
            setl.current_work = Construction(most_capacity[1])
        else:
            # Aggressive AIs will, in most cases, pick the available unit with the most power, if the settlement level
            # is high enough. However, if they do not have an acceptable number of healer units (20% of total), one of
            # those will be selected instead.
            match player.ai_playstyle.attacking:
                case AttackPlaystyle.AGGRESSIVE:
                    if len(player.units) < setl.level:
                        existing_healers = [u for u in player.units if u.plan.heals]
                        units_to_use = avail_units
                        if player.units and healer_units and (len(existing_healers) / len(player.units) < 0.2):
                            units_to_use = healer_units
                        most_power: (float, UnitPlan) = units_to_use[0].power, units_to_use[0]
                        for up in units_to_use:
                            if up.power >= most_power[0]:
                                most_power = up.power, up
                        setl.current_work = Construction(most_power[1])
                    else:
                        setl.current_work = Construction(ideal)
                # If they are lacking in units, defensive AIs will pick either the available unit with the most health
                # or a healer unit if they do not have enough (50% of total). Alternatively, they will choose the
                # improvement that yields the most strength for the settlement, if there is one, otherwise, they will
                # choose the 'ideal' construction.
                case AttackPlaystyle.DEFENSIVE:
                    if len(player.units) * 2 < setl.level:
                        existing_healers = [u for u in player.units if u.plan.heals]
                        if player.units and healer_units and (len(existing_healers) / len(player.units) < 0.5):
                            most_power: (float, UnitPlan) = healer_units[0].power, healer_units[0]
                            for up in healer_units:
                                if up.power >= most_power[0]:
                                    most_power = up.power, up
                            setl.current_work = Construction(most_power[1])
                        else:
                            most_health: (float, UnitPlan) = avail_units[0].max_health, avail_units[0]
                            for up in avail_units:
                                if up.max_health >= most_health[0]:
                                    most_health = up.max_health, up
                            setl.current_work = Construction(most_health[1])
                    elif len(strength_imps := [imp for imp in avail_imps if imp.effect.strength > 0]) > 0:
                        setl.current_work = Construction(strength_imps[0])
                    else:
                        setl.current_work = Construction(ideal)
                # Neutral AIs will always choose the 'ideal' construction.
                case _:
                    setl.current_work = Construction(ideal)
    # If the selected construction ended up being an improvement that requires resources, subtract those from the AI
    # player's total.
    if isinstance(cons := setl.current_work.construction, Improvement) and cons.req_resources:
        subtract_player_resources_for_improvement(player, cons)


def search_for_relics_or_move(unit: Unit,
                              quads: List[List[Quad]],
                              player: Player,
                              other_units: List[Unit],
                              all_setls: List[Settlement],
                              cfg: GameConfig):
    """
    Units that have no action to take can look for relics, or just simply move randomly.
    :param unit: The unit to move.
    :param quads: The game quads.
    :param player: The current AI player.
    :param other_units: All the other units in the game.
    :param all_setls: All the settlements in the game.
    :param cfg: The current game configuration.
    """
    # The range in which a unit can investigate is actually further than its remaining stamina, as you only
    # have to be next to a relic to investigate it.
    investigate_range = unit.remaining_stamina + 1
    for i in range(unit.location[0] - investigate_range, unit.location[0] + investigate_range + 1):
        for j in range(unit.location[1] - investigate_range, unit.location[1] + investigate_range + 1):
            if 0 <= i <= 99 and 0 <= j <= 89 and quads[j][i].is_relic:
                first_resort: (int, int)
                second_resort = i, j + 1
                third_resort = i, j - 1
                if i - unit.location[0] < 0:
                    first_resort = i + 1, j
                else:
                    first_resort = i - 1, j
                found_valid_loc = False
                for loc in [first_resort, second_resort, third_resort]:
                    if not any(u.location == loc for u in player.units) and \
                            not any(other_u.location == loc for other_u in other_units) and \
                            not any(any(setl_quad.location == loc for setl_quad in setl.quads) for setl in all_setls):
                        unit.location = loc
                        update_player_quads_seen_around_point(player, loc)
                        found_valid_loc = True
                        unit.remaining_stamina = 0
                        break
                if found_valid_loc:
                    investigate_relic(player, unit, (i, j), cfg)
                    quads[j][i].is_relic = False
                    return
    # We only get to this point if a valid relic was not found. Make sure when moving randomly that the unit does not
    # collide with other units or settlements. We only try to move five times because technically a unit could have
    # nowhere to move and this could loop forever.
    for _ in range(5):
        x_movement = random.randint(-unit.remaining_stamina, unit.remaining_stamina)
        rem_movement = unit.remaining_stamina - abs(x_movement)
        y_movement = random.choice([-rem_movement, rem_movement])
        loc = clamp(unit.location[0] + x_movement, 0, 99), clamp(unit.location[1] + y_movement, 0, 89)
        if not any(u.location == loc and u != unit for u in player.units) and \
                not any(other_u.location == loc for other_u in other_units) and \
                not any(any(setl_quad.location == loc for setl_quad in setl.quads) for setl in all_setls):
            unit.location = loc
            update_player_quads_seen_around_point(player, loc)
            unit.remaining_stamina -= abs(x_movement) + abs(y_movement)
            break


def move_healer_unit(player: Player, unit: Unit, other_units: List[Unit],
                     all_setls: List[Settlement], quads: List[List[Quad]], cfg: GameConfig):
    """
    Search for any friendly units within range that aren't at full health. If one is found, move next to it and
    heal it. Otherwise, the healer unit looks for relics or moves randomly.
    :param player: The player owner of the healer unit.
    :param unit: The healer unit itself.
    :param other_units: The other units in the game. Used to make sure no unit collisions occur.
    :param all_setls: All of the settlements in the game. Used to make sure no collisions occur between the healer unit
    and settlements.
    :param quads: The quads on the board.
    :param cfg: The current game configuration.
    """
    within_range: Optional[Unit] = None
    for player_u in player.units:
        if max(abs(unit.location[0] - player_u.location[0]),
               abs(unit.location[1] - player_u.location[1])) <= unit.remaining_stamina and \
                player_u.health < player_u.plan.max_health and player_u is not unit:
            within_range = player_u
            break
    if within_range is not None:
        # Now that we have determined that there is another unit for our unit to heal, we need to work out where
        # we will move our unit to. There are three options for this, directly to the sides of the unit, below
        # the unit, or above the unit.
        first_resort: (int, int)
        second_resort = within_range.location[0], within_range.location[1] + 1
        third_resort = within_range.location[0], within_range.location[1] - 1
        if within_range.location[0] - unit.location[0] < 0:
            first_resort = within_range.location[0] + 1, within_range.location[1]
        else:
            first_resort = within_range.location[0] - 1, within_range.location[1]
        found_valid_loc = False
        # We have to ensure that no other units or settlements are in the location we intend to move to.
        for loc in [first_resort, second_resort, third_resort]:
            if not any(u.location == loc for u in player.units) and \
                    not any(other_u.location == loc for other_u in other_units) and \
                    not any(any(setl_quad.location == loc for setl_quad in setl.quads) for setl in all_setls):
                unit.location = loc
                update_player_quads_seen_around_point(player, loc)
                found_valid_loc = True
                unit.remaining_stamina = 0
                break
        # Assuming we found a valid location, the healing can take place.
        if found_valid_loc:
            heal(unit, within_range)
    # If there's nothing within range, look for relics or just move randomly.
    else:
        search_for_relics_or_move(unit, quads, player, other_units, all_setls, cfg)


def get_unit_setl_distance(u: Unit, s: Settlement) -> (float, int, int):
    """
    Calculate the distance as the crow flies between the supplied unit and settlement, while also returning the raw
    X and Y differences in position.
    :param u: The unit having its location read.
    :param s: The settlement having its location read.
    :return: A tuple with three elements - the raw distance, and the discrete X and Y differences.
    """
    dist = pow(pow(x_d := (s.location[0] - u.location[0]), 2) +
               pow(y_d := (s.location[1] - u.location[1]), 2), 0.5)
    return dist, x_d, y_d


class MoveMaker:
    """
    The MoveMaker class handles AI moves for each turn.
    """

    def __init__(self, namer: Namer):
        """
        Initialise the MoveMaker's Namer reference.
        :param namer: The Namer instance to use for settlement names.
        """
        self.namer: Namer = namer
        self.board_ref = None

    def make_move(self, player: Player, all_players: List[Player], quads: List[List[Quad]],
                  cfg: GameConfig, is_night: bool, local_player_idx: Optional[int]):
        """
        Make a move for the given AI player.
        :param player: The AI player to make a move for.
        :param all_players: The list of all players.
        :param quads: The 2D list of quads to use to search for relics.
        :param cfg: The game configuration.
        :param is_night: Whether it is night.
        :param local_player_idx: The index of the player on this machine in the overall players list.
        """
        all_setls = []
        for pl in all_players:
            all_setls.extend(pl.settlements)
        other_player_vics = list((p, len(p.imminent_victories)) for p in all_players
                                 if p.imminent_victories and p is not player)
        player_totals = get_player_totals(player, is_night)
        overall_wealth = player_totals[0]
        if player.ongoing_blessing is None:
            set_blessing(player, player_totals)
        for setl in player.settlements:
            if setl.current_work is None:
                set_ai_construction(player, setl, is_night, other_player_vics)
            elif player.faction != Faction.FUNDAMENTALISTS:
                cons = setl.current_work.construction
                # If the buyout cost for the settlement is less than a third of the player's wealth, buy it out. In
                # circumstances where the settlement's satisfaction is less than 50 and the construction would yield
                # harvest or satisfaction, buy it out as soon as the AI is able to afford it. Fundamentalist AIs are
                # exempt from this, as they cannot buy out constructions.
                if not isinstance(cons, Project) and \
                        ((cons.cost - setl.current_work.zeal_consumed) < player.wealth / 3 or
                         (setl.satisfaction < 50 and player.wealth >= cons.cost and isinstance(cons, Improvement) and
                          (cons.effect.satisfaction > 0 or cons.effect.harvest > 0))):
                    player.wealth -= cons.cost - setl.current_work.zeal_consumed
                    complete_construction(setl, player)
            # If the settlement has a settler, deploy them.
            if len(settlers := [unit for unit in setl.garrison if unit.plan.can_settle]) > 0:
                for settler in settlers:
                    settler.garrisoned = False
                    settler.location = next(loc for loc in gen_spiral_indices(setl.location)
                                            if not any(setl_quad.location == loc for setl_quad in setl.quads) and
                                            0 <= loc[0] <= 99 and 0 <= loc[1] <= 89)
                    player.units.append(settler)
                    update_player_quads_seen_around_point(player, settler.location)
                    setl.garrison.remove(settler)
            # Deploy a unit from the garrison if the AI is not defensive, or the settlement is under siege or attack, or
            # there are too many units garrisoned.
            if (len(setl.garrison) > 0 and
                (player.ai_playstyle.attacking != AttackPlaystyle.DEFENSIVE or setl.besieged
                 or setl.strength < setl.max_strength / 2)) or len(setl.garrison) > 3:
                deployed = setl.garrison.pop()
                deployed.garrisoned = False
                deployed.location = next(loc for loc in gen_spiral_indices(setl.location)
                                         if not any(setl_quad.location == loc for setl_quad in setl.quads) and
                                         0 <= loc[0] <= 99 and 0 <= loc[1] <= 89)
                player.units.append(deployed)
                update_player_quads_seen_around_point(player, deployed.location)
            # If another player is close to a victory, and there are deployer units in the garrison, deploy all of them.
            if other_player_vics and \
                    len(deployers := [unit for unit in setl.garrison if isinstance(unit, DeployerUnit)]) > 0:
                for deployer in deployers:
                    deployer.garrisoned = False
                    deployer.location = next(loc for loc in gen_spiral_indices(setl.location)
                                             if not any(setl_quad.location == loc for setl_quad in setl.quads) and
                                             0 <= loc[0] <= 99 and 0 <= loc[1] <= 89)
                    player.units.append(deployer)
                    update_player_quads_seen_around_point(player, deployer.location)
                    setl.garrison.remove(deployer)
        all_units = []
        for p in all_players:
            if p is not player:
                for unit in p.units:
                    all_units.append(unit)
        min_pow_health: Tuple[float, Unit] = 9999, None  # 9999 is arbitrary, but no unit will ever have this.
        # Move each deployed unit, and also work out which of the player's units has the lowest combined power and
        # health. This is subsequently used if we need to sell units due to negative wealth.
        for unit in player.units:
            if pow_health := (unit.health + unit.plan.power) < min_pow_health[0]:
                min_pow_health = pow_health, unit
            self.move_unit(player, unit, all_units, all_players, all_setls, quads, cfg, other_player_vics,
                           local_player_idx)
            overall_wealth -= unit.plan.cost / 10
        if (player.wealth + overall_wealth < 0) and min_pow_health[1] in player.units:
            player.wealth += min_pow_health[1].plan.cost
            player.units.remove(min_pow_health[1])

    def move_settler_unit(self, unit: Unit, player: Player, other_units: List[Unit], all_setls: List[Settlement]):
        """
        Randomly move the given settler until it is both far enough away from any of the player's other settlements and
        next to one or more core resources, ensuring that it does not collide with any other units or settlements. Once
        this has been achieved, found a new settlement and destroy the unit.
        :param unit: The settler unit.
        :param player: The player owner of the settler unit.
        :param other_units: The other units in the game. Used to make sure no unit collisions occur.
        :param all_setls: All of the settlements in the game. Used to make sure no collisions occur between the settler
        and settlements.
        """
        # We only try to move five times because technically a unit could have nowhere to move and this could loop
        # forever.
        for _ in range(5):
            x_movement = random.randint(-unit.remaining_stamina, unit.remaining_stamina)
            rem_movement = unit.remaining_stamina - abs(x_movement)
            y_movement = random.choice([-rem_movement, rem_movement])
            loc = clamp(unit.location[0] + x_movement, 0, 99), clamp(unit.location[1] + y_movement, 0, 89)
            if not any(u.location == loc and u != unit for u in player.units) and \
                    not any(other_u.location == loc for other_u in other_units) and \
                    not any(any(setl_quad.location == loc for setl_quad in setl.quads) for setl in all_setls):
                unit.location = loc
                update_player_quads_seen_around_point(player, loc)
                unit.remaining_stamina -= abs(x_movement) + abs(y_movement)
                break

        should_settle = True
        for setl in player.settlements:
            dist = max(abs(unit.location[0] - setl.location[0]), abs(unit.location[1] - setl.location[1]))
            if dist < 10:
                should_settle = False
        prospective_quad: Quad = self.board_ref.quads[unit.location[1]][unit.location[0]]
        prospective_resources: ResourceCollection = \
            get_resources_for_settlement([prospective_quad.location], self.board_ref.quads)
        # We make sure that AI settler units only settle next to core resources so that they don't end up in a situation
        # where they are missing the necessary core resources to construct improvements, and as a result, are unable to
        # effectively compete with human players to win the game.
        if not prospective_resources.ore and not prospective_resources.timber and not prospective_resources.magma:
            should_settle = False
        if should_settle:
            quad_biome = prospective_quad.biome
            setl_name = self.namer.get_settlement_name(quad_biome)
            setl_resources = get_resources_for_settlement([unit.location], self.board_ref.quads)
            new_settl = Settlement(setl_name, unit.location, [], [prospective_quad], setl_resources, [])
            if player.faction == Faction.FRONTIERSMEN:
                new_settl.satisfaction = 75.0
            elif player.faction == Faction.IMPERIALS:
                new_settl.strength /= 2
                new_settl.max_strength /= 2
            if new_settl.resources.obsidian:
                new_settl.strength *= (1 + 0.5 * new_settl.resources.obsidian)
                new_settl.max_strength *= (1 + 0.5 * new_settl.resources.obsidian)
            player.settlements.append(new_settl)
            update_player_quads_seen_around_point(player, new_settl.location)
            player.units.remove(unit)

    def move_unit(self, player: Player, unit: Unit, other_units: List[Unit], all_players: List[Player],
                  all_setls: List[Settlement], quads: List[List[Quad]], cfg: GameConfig,
                  other_player_vics: List[Tuple[Player, int]], local_player_idx: Optional[int]):
        """
        Move the given unit, attacking if the right conditions are met.
        :param player: The AI owner of the unit being moved.
        :param unit: The unit being moved.
        :param other_units: The list of all enemy units.
        :param all_players: The list of all players.
        :param all_setls: The list of all settlements.
        :param quads: The 2D list of quads to use to search for relics.
        :param cfg: The game configuration.
        :param other_player_vics: A list of tuples of players and the number of imminent victories they have. Note that
        players without any imminent victories are not included in this list.
        :param local_player_idx: The index of the player on this machine in the overall players list.
        """
        # If the unit can settle, randomly move it until it is far enough away from any of the player's other
        # settlements, ensuring that it does not collide with any other units or settlements. Once this has been
        # achieved, found a new settlement and destroy the unit.
        if unit.plan.can_settle:
            self.move_settler_unit(unit, player, other_units, all_setls)
        # If the unit is a healer, look around for any friendly units within range that aren't at full health. If one is
        # found, move next to it and heal it. Otherwise, just look for relics or move randomly.
        elif unit.plan.heals:
            move_healer_unit(player, unit, other_units, all_setls, quads, cfg)
        # If the unit is a deployer unit, behaviour differs based on whether other players have imminent victories.
        elif isinstance(unit, DeployerUnit):
            if other_player_vics:
                # If another player is close to a victory and the deployer unit is empty of passengers, move to the
                # nearest settlement, if a move is required at all. There are two cases where this will occur - the
                # first is when the deployer unit has first been deployed and no units have become passengers yet, and
                # the second is when the deployer unit has moved to an enemy settlement and deployed all units, now
                # needing to return.
                if not unit.passengers:
                    nearest_settlement: (Settlement, float, int, int) = \
                        player.settlements[0], *get_unit_setl_distance(unit, player.settlements[0])
                    for setl in player.settlements:
                        distance = get_unit_setl_distance(unit, setl)
                        if distance[0] < nearest_settlement[1]:
                            nearest_settlement = setl, *distance
                    # We use half of the deployer unit's remaining stamina here so that the unit may overshoot the
                    # settlement, but still end up closer than before the move.
                    if nearest_settlement[1] > unit.remaining_stamina / 2:
                        dir_vec = (nearest_settlement[2] / nearest_settlement[1],
                                   nearest_settlement[3] / nearest_settlement[1])
                        unit.location = (int(unit.location[0] + dir_vec[0] * unit.remaining_stamina),
                                         int(unit.location[1] + dir_vec[1] * unit.remaining_stamina))
                        update_player_quads_seen_around_point(player, unit.location)
                        unit.remaining_stamina = 0
                # Deployer units at max capacity move towards the weakest settlement belonging to the player with the
                # most imminent victories.
                else:
                    player_with_most_vics = max(other_player_vics, key=operator.itemgetter(1))[0]
                    weakest_settlement: (Settlement, int) = \
                        player_with_most_vics.settlements[0], player_with_most_vics.settlements[0].strength
                    for setl in player_with_most_vics.settlements:
                        if setl.strength < weakest_settlement[1]:
                            weakest_settlement = setl, setl.strength
                    distance, x_diff, y_diff = get_unit_setl_distance(unit, weakest_settlement[0])
                    # Once the unit arrives at the weakest settlement, it deploys the first of its passengers.
                    if distance < unit.remaining_stamina:
                        deployed = unit.passengers.pop()
                        deployed.location = next(loc for loc in gen_spiral_indices(unit.location) if
                                                 not any(unit.location == loc for unit in player.units) and
                                                 not any(unit.location == loc for unit in other_units) and
                                                 not any(any(setl_quad.location == loc for setl_quad in setl.quads)
                                                         for setl in all_setls) and
                                                 0 <= loc[0] <= 99 and 0 <= loc[1] <= 89)
                        player.units.append(deployed)
                        update_player_quads_seen_around_point(player, deployed.location)
                    elif len(unit.passengers) == unit.plan.max_capacity:
                        dir_vec = (x_diff / distance, y_diff / distance)
                        unit.location = (int(unit.location[0] + dir_vec[0] * unit.remaining_stamina),
                                         int(unit.location[1] + dir_vec[1] * unit.remaining_stamina))
                        update_player_quads_seen_around_point(player, unit.location)
                        unit.remaining_stamina = 0
            # If there are no other players with imminent victories, deployer units can just explore.
            else:
                search_for_relics_or_move(unit, quads, player, other_units, all_setls, cfg)
        else:
            attack_over_siege = True  # If False, the unit will siege the settlement.
            within_range: Optional[Unit | Settlement] = None
            # If the unit cannot settle, then we must first check if it meets the criteria to attack another unit. A
            # unit can attack if one or more of the following apply:
            # - Any of its settlements are under siege or attack
            # - If the AI is aggressive
            # - If the AI is neutral but with a health advantage over another unit
            # - If the other unit is an Infidel
            # - If the other unit belongs to a player with an imminent Elimination victory
            for other_u in other_units:
                is_infidel = False
                is_close_to_elimination_vic = False
                for pl in all_players:
                    if pl.faction == Faction.INFIDELS and other_u in pl.units:
                        is_infidel = True
                        break
                    if VictoryType.ELIMINATION in pl.imminent_victories:
                        is_close_to_elimination_vic = True
                        break
                could_attack: bool = any(setl.besieged or setl.strength < setl.max_strength / 2
                                         for setl in player.settlements) or \
                    player.ai_playstyle.attacking == AttackPlaystyle.AGGRESSIVE or \
                    (player.ai_playstyle.attacking == AttackPlaystyle.NEUTRAL and
                     unit.health >= other_u.health * 2) or is_infidel or is_close_to_elimination_vic
                # Of course, the attacked unit has to be close enough.
                if max(abs(unit.location[0] - other_u.location[0]),
                       abs(unit.location[1] - other_u.location[1])) <= unit.remaining_stamina and could_attack and \
                        other_u is not unit:
                    within_range = other_u
                    break
            if within_range is None:
                # If there are no other units within range and attackable, then we check if there are any enemy
                # settlements we can attack or place under siege.
                for other_setl in all_setls:
                    setl_owner = None
                    for pl in all_players:
                        if other_setl in pl.settlements:
                            setl_owner = pl
                    if setl_owner is not player:
                        # Settlements are only attacked by AI players under strict conditions. Even aggressive AIs need
                        # to double the strength of the settlement in their health. However, these strict conditions are
                        # ignored in times of desperation, i.e. when the other player has an imminent victory.
                        could_attack: bool = (player.ai_playstyle.attacking == AttackPlaystyle.AGGRESSIVE and
                                              unit.health >= other_setl.strength * 2) or \
                                             (player.ai_playstyle.attacking == AttackPlaystyle.NEUTRAL and
                                              unit.health >= other_setl.strength * 10) or \
                                             (player.ai_playstyle.attacking == AttackPlaystyle.DEFENSIVE and
                                              other_setl.strength == 0) or setl_owner.imminent_victories
                        if could_attack:
                            if any(max(abs(unit.location[0] - setl_quad.location[0]),
                                       abs(unit.location[1] - setl_quad.location[1])) <= unit.remaining_stamina
                                   for setl_quad in other_setl.quads):
                                within_range = other_setl
                                break
                        else:
                            # If there are no attackable settlements, we check if the AI player can place any under
                            # siege. Aggressive AIs will place any settlement they can see under siege, and neutral AIs
                            # will do the same if they have the upper hand.
                            could_siege: bool = player.ai_playstyle.attacking == AttackPlaystyle.AGGRESSIVE or \
                                                (player.ai_playstyle.attacking == AttackPlaystyle.NEUTRAL and
                                                 unit.health >= other_setl.strength * 2)
                            if could_siege:
                                if any(max(abs(unit.location[0] - setl_quad.location[0]),
                                           abs(unit.location[1] - setl_quad.location[1])) <= unit.remaining_stamina
                                       for setl_quad in other_setl.quads):
                                    within_range = other_setl
                                    attack_over_siege = False
                                    break
            if within_range is not None:
                # Now that we have determined that there is some entity (unit or settlement) that our unit will attack,
                # we need to work out where we will move our unit to, if at all. There are three options for this,
                # directly to the sides of the entity, below the entity, or above the entity. Alternatively, if our unit
                # is already adjacent to the entity to be attacked, don't bother moving at all.
                found_valid_loc = False
                if abs(unit.location[0] - within_range.location[0]) > 1 or \
                   abs(unit.location[1] - within_range.location[1]) > 1:
                    first_resort: (int, int)
                    second_resort = within_range.location[0], within_range.location[1] + 1
                    third_resort = within_range.location[0], within_range.location[1] - 1
                    if within_range.location[0] - unit.location[0] < 0:
                        first_resort = within_range.location[0] + 1, within_range.location[1]
                    else:
                        first_resort = within_range.location[0] - 1, within_range.location[1]
                    # We have to ensure that no other units or settlements are in the location we intend to move to.
                    for loc in [first_resort, second_resort, third_resort]:
                        if not any(u.location == loc for u in player.units) and \
                                not any(other_u.location == loc for other_u in other_units) and \
                                not any(any(setl_quad.location == loc for setl_quad in setl.quads)
                                        for setl in all_setls):
                            unit.location = loc
                            update_player_quads_seen_around_point(player, unit.location)
                            unit.remaining_stamina = 0
                            found_valid_loc = True
                            break
                else:
                    found_valid_loc = True
                # If there is no location we can move to that allows us to attack, don't move or attack.
                if found_valid_loc:
                    if attack_over_siege:
                        # If we are attacking another unit, we stop our siege first, and then attack.
                        if isinstance(within_range, Unit):
                            unit.besieging = False
                            data = attack(unit, within_range)

                            # Show the attack notification if we attacked the human player on this machine.
                            if local_player_idx is not None and within_range in all_players[local_player_idx].units:
                                self.board_ref.overlay.toggle_attack(data)
                                # Also deselect the unit if it was killed while selected.
                                if within_range.health <= 0 and self.board_ref.overlay.selected_unit is within_range:
                                    self.board_ref.overlay.toggle_unit(None)
                                    self.board_ref.overlay.selected_unit = None
                            if within_range.health <= 0:
                                for p in all_players:
                                    if within_range in p.units:
                                        p.units.remove(within_range)
                                        break
                            if unit.health <= 0:
                                player.units.remove(unit)
                        # Alternatively, we are attacking a settlement.
                        else:
                            setl_owner = None
                            for pl in all_players:
                                if within_range.name in [setl.name for setl in pl.settlements]:
                                    setl_owner = pl
                            # If the player is of the Concentrated faction, and they just took the settlement this unit
                            # was planning to attack, then the settlement will cease to exist. As such, only proceed
                            # with the attack if we can find the owner, and thus, the settlement.
                            if setl_owner:
                                data = attack_setl(unit, within_range, setl_owner)

                                # Show the settlement attack notification if we attacked the human player on this
                                # machine.
                                if local_player_idx is not None and \
                                        within_range in all_players[local_player_idx].settlements:
                                    self.board_ref.overlay.toggle_setl_attack(data)
                                if data.attacker_was_killed:
                                    player.units.remove(data.attacker)
                                elif data.setl_was_taken:
                                    data.settlement.besieged = False
                                    for u in player.units:
                                        if any(abs(u.location[0] - setl_quad.location[0]) <= 1 and
                                               abs(u.location[1] - setl_quad.location[1]) <= 1
                                               for setl_quad in data.settlement.quads):
                                            u.besieging = False
                                    if player.faction != Faction.CONCENTRATED:
                                        player.settlements.append(data.settlement)
                                        update_player_quads_seen_around_point(player, data.settlement.location)
                                    setl_owner.settlements.remove(data.settlement)
                    # If we have chosen to place a settlement under siege, and the unit is not already besieging another
                    # settlement, do so.
                    elif not unit.besieging:
                        unit.besieging = True
                        if not within_range.besieged:
                            within_range.besieged = True
                            # Show the siege notification if we have placed a settlement under siege that belongs to the
                            # human player on this machine.
                            if local_player_idx is not None and \
                                    within_range in all_players[local_player_idx].settlements:
                                self.board_ref.overlay.toggle_siege_notif(within_range, player)
            # If a suitable unit or settlement was not found to attack, but there is another player with an imminent
            # victory, either move into a deployer unit or move towards the weakest settlement belonging to the player
            # with the most imminent victories.
            elif other_player_vics:
                # Attempt to move into a nearby deployer unit to begin with.
                for player_u in player.units:
                    if max(abs(unit.location[0] - player_u.location[0]),
                           abs(unit.location[1] - player_u.location[1])) <= unit.remaining_stamina and \
                            isinstance(player_u, DeployerUnit) and \
                            len(player_u.passengers) < player_u.plan.max_capacity:
                        unit.remaining_stamina = 0
                        player_u.passengers.append(unit)
                        player.units.remove(unit)
                        break
                # I.e. the unit did not find a deployer to board.
                if unit.remaining_stamina:
                    player_with_most_vics = max(other_player_vics, key=operator.itemgetter(1))[0]
                    weakest_settlement: (Settlement, int) = \
                        player_with_most_vics.settlements[0], player_with_most_vics.settlements[0].strength
                    for setl in player_with_most_vics.settlements:
                        if setl.strength < weakest_settlement[1]:
                            weakest_settlement = setl, setl.strength
                    distance, x_diff, y_diff = get_unit_setl_distance(unit, weakest_settlement[0])
                    dir_vec = (x_diff / distance, y_diff / distance)
                    unit.location = (int(unit.location[0] + dir_vec[0] * unit.remaining_stamina),
                                     int(unit.location[1] + dir_vec[1] * unit.remaining_stamina))
                    update_player_quads_seen_around_point(player, unit.location)
                    unit.remaining_stamina = 0
            # If there's nothing within range, look for relics or just move randomly.
            else:
                search_for_relics_or_move(unit, quads, player, other_units, all_setls, cfg)
