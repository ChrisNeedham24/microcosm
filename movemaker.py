import random
import typing

from board import Board
from calculator import get_player_totals, get_setl_totals, attack, complete_construction, clamp, attack_setl
from catalogue import get_available_blessings, get_unlockable_improvements, get_unlockable_units, \
    get_available_improvements, get_available_unit_plans, get_settlement_name
from models import Player, Blessing, AIPlaystyle, OngoingBlessing, Settlement, Improvement, UnitPlan, Construction, Unit
from overlay import Overlay


class MoveMaker:
    def __init__(self):
        self.board_ref = None

    def make_move(self, player: Player, all_players: typing.List[Player]):
        all_setls = []
        for pl in all_players:
            all_setls.extend(pl.settlements)
        player_totals = get_player_totals(player)
        if player.ongoing_blessing is None:
            self.set_blessing(player, player_totals)
        for setl in player.settlements:
            if setl.current_work is None:
                self.set_construction(player, setl)
            else:
                if rem_work := (setl.current_work.construction.cost - setl.current_work.zeal_consumed) < player.wealth / 3:
                    complete_construction(setl)
                    player.wealth -= rem_work
            if len([unit for unit in setl.garrison if unit.plan.can_settle]) > 0:
                for unit in setl.garrison:
                    if unit.plan.can_settle:
                        unit.garrisoned = False
                        unit.location = setl.location[0], setl.location[1] + 1
                        player.units.append(unit)
                        setl.garrison.remove(unit)
            if (len(setl.garrison) > 0 and
                (player.ai_playstyle is not AIPlaystyle.DEFENSIVE or setl.under_siege_by is not None
                 or setl.strength < setl.max_strength / 2)) or \
                    len(setl.garrison) > 3:
                deployed = setl.garrison.pop()
                deployed.garrisoned = False
                deployed.location = setl.location[0], setl.location[1] + 1
                player.units.append(deployed)
        all_units = []
        for p in all_players:
            if p is not player:
                for unit in p.units:
                    all_units.append(unit)
        min_pow_health: (float, Unit) = 9999, None  # 999 is arbitrary, but no unit will ever have this.
        for unit in player.units:
            if pow_health := (unit.health + unit.plan.power) < min_pow_health[0]:
                min_pow_health = pow_health, unit
            self.move_unit(player, unit, all_units, all_players, all_setls)
        if player.wealth + player_totals[0] < 0:
            player.wealth += min_pow_health[1].plan.cost
            player.units.remove(min_pow_health[1])


    def set_blessing(self, player: Player, player_totals: (float, float, float, float)):
        avail_bless = get_available_blessings(player)
        if len(avail_bless) > 0:
            ideal: Blessing = avail_bless[0]
            lowest = player_totals.index(min(player_totals))
            if lowest == 0:
                highest_wealth: (float, Blessing) = 0, avail_bless[0]
                for bless in avail_bless:
                    cumulative_wealth: float = 0
                    for imp in get_unlockable_improvements(bless):
                        cumulative_wealth += imp.effect.wealth
                    if cumulative_wealth > highest_wealth[0]:
                        highest_wealth = cumulative_wealth, bless
                ideal = highest_wealth[1]
            if lowest == 1:
                highest_harvest: (float, Blessing) = 0, avail_bless[0]
                for bless in avail_bless:
                    cumulative_harvest: float = 0
                    for imp in get_unlockable_improvements(bless):
                        cumulative_harvest += imp.effect.harvest
                    if cumulative_harvest > highest_harvest[0]:
                        highest_harvest = cumulative_harvest, bless
                ideal = highest_harvest[1]
            if lowest == 2:
                highest_zeal: (float, Blessing) = 0, avail_bless[0]
                for bless in avail_bless:
                    cumulative_zeal: float = 0
                    for imp in get_unlockable_improvements(bless):
                        cumulative_zeal += imp.effect.zeal
                    if cumulative_zeal > highest_zeal[0]:
                        highest_zeal = cumulative_zeal, bless
                ideal = highest_zeal[1]
            if lowest == 3:
                highest_fortune: (float, Blessing) = 0, avail_bless[0]
                for bless in avail_bless:
                    cumulative_fortune: float = 0
                    for imp in get_unlockable_improvements(bless):
                        cumulative_fortune += imp.effect.fortune
                    if cumulative_fortune > highest_fortune[0]:
                        highest_fortune = cumulative_fortune, bless
                ideal = highest_fortune[1]
            if player.ai_playstyle is AIPlaystyle.AGGRESSIVE:
                for bless in avail_bless:
                    unlockable = get_unlockable_units(bless)
                    if len(unlockable) > 0:
                        player.ongoing_blessing = OngoingBlessing(bless)
                        break
                if player.ongoing_blessing is None:
                    player.ongoing_blessing = OngoingBlessing(ideal)
            elif player.ai_playstyle is AIPlaystyle.DEFENSIVE:
                for bless in avail_bless:
                    unlockable = get_unlockable_improvements(bless)
                    if len([imp for imp in unlockable if imp.effect.strength > 0]) > 0:
                        player.ongoing_blessing = OngoingBlessing(bless)
                        break
                if player.ongoing_blessing is None:
                    player.ongoing_blessing = OngoingBlessing(ideal)
            else:
                player.ongoing_blessing = OngoingBlessing(ideal)

    def set_construction(self, player: Player, setl: Settlement):
        avail_imps = get_available_improvements(player, setl)
        avail_units = get_available_unit_plans(player, setl.level)
        settler_units = [settler for settler in avail_units if settler.can_settle]
        ideal: typing.Union[Improvement, UnitPlan] = avail_imps[0] if len(avail_imps) > 0 else avail_units[0]
        if len(player.units) == 0 and len(setl.garrison) == 0:
            setl.current_work = Construction(avail_units[0])
        elif setl.level >= 3 and not setl.produced_settler:
            setl.current_work = Construction(settler_units[0])
        else:
            if len(avail_imps) > 0:
                totals = get_setl_totals(setl)
                lowest = totals.index(min(totals))
                if lowest == 0:
                    highest_wealth: (float, Improvement) = avail_imps[0].effect.wealth, avail_imps[0]
                    for imp in avail_imps:
                        if imp.effect.wealth > highest_wealth[0]:
                            highest_wealth = imp.effect.wealth, imp
                    ideal = highest_wealth[1]
                if lowest == 1:
                    highest_harvest: (float, Improvement) = avail_imps[0].effect.harvest, avail_imps[0]
                    for imp in avail_imps:
                        if imp.effect.harvest > highest_harvest[0]:
                            highest_harvest = imp.effect.harvest, imp
                    ideal = highest_harvest[1]
                if lowest == 2:
                    highest_zeal: (float, Improvement) = avail_imps[0].effect.zeal, avail_imps[0]
                    for imp in avail_imps:
                        if imp.effect.zeal > highest_zeal[0]:
                            highest_zeal = imp.effect.zeal, imp
                    ideal = highest_zeal[1]
                if lowest == 3:
                    highest_fortune: (float, Improvement) = avail_imps[0].effect.fortune, avail_imps[0]
                    for imp in avail_imps:
                        if imp.effect.fortune > highest_fortune[0]:
                            highest_fortune = imp.effect.fortune, imp
                    ideal = highest_fortune[1]

            if player.ai_playstyle is AIPlaystyle.AGGRESSIVE:
                if len(player.units) < setl.level:
                    most_power: (float, UnitPlan) = avail_units[0].power, avail_units[0]
                    for up in avail_units:
                        if up.power >= most_power[0]:
                            most_power = up.power, up
                    setl.current_work = Construction(most_power[1])
                else:
                    setl.current_work = Construction(ideal)
            elif player.ai_playstyle is AIPlaystyle.DEFENSIVE:
                if len(player.units) * 2 < setl.level:
                    most_health: (float, UnitPlan) = avail_units[0].max_health, avail_units[0]
                    for up in avail_units:
                        if up.max_health >= most_health[0]:
                            most_health = up.max_health, up
                    setl.current_work = Construction(most_health[1])
                elif len(strength_imps := [imp for imp in avail_imps if imp.effect.strength > 0]) > 0:
                    setl.current_work = Construction(strength_imps[0])
                else:
                    setl.current_work = Construction(ideal)
            else:
                setl.current_work = Construction(ideal)

    def move_unit(self, player: Player, unit: Unit, other_units: typing.List[Unit], all_players: typing.List[Player],
                  all_setls: typing.List[Settlement]):
        if unit.plan.can_settle:
            x_movement = random.randint(-unit.remaining_stamina, unit.remaining_stamina)
            rem_movement = unit.remaining_stamina - abs(x_movement)
            y_movement = random.choice([-rem_movement, rem_movement])
            unit.location = clamp(unit.location[0] + x_movement, 0, 99), clamp(unit.location[1] + y_movement, 0, 89)
            unit.remaining_stamina -= abs(x_movement) + abs(y_movement)

            far_enough = True
            for setl in player.settlements:
                dist = max(abs(unit.location[0] - setl.location[0]), abs(unit.location[1] - setl.location[1]))
                if dist < 10:
                    far_enough = False
            if far_enough:
                quad_biome = self.board_ref.quads[unit.location[1]][unit.location[0]].biome
                setl_name = get_settlement_name(quad_biome)
                new_settl = Settlement(setl_name, unit.location, [],
                                       [self.board_ref.quads[unit.location[1]][unit.location[0]]], [])
                player.settlements.append(new_settl)
                player.units.remove(unit)
        else:
            attack_over_siege = True  # If False, the unit will siege the settlement.
            within_range: typing.Optional[typing.Union[Unit, Settlement]] = None
            for other_u in other_units:
                could_attack: bool = any(setl.under_siege_by is not None or setl.strength < setl.max_strength / 2
                                         for setl in player.settlements) or \
                                     player.ai_playstyle is AIPlaystyle.AGGRESSIVE or \
                                     (player.ai_playstyle is AIPlaystyle.NEUTRAL and unit.health >= other_u.health * 2)
                if max(abs(unit.location[0] - other_u.location[0]),
                       abs(unit.location[1] - other_u.location[1])) <= unit.remaining_stamina and could_attack and \
                        other_u is not unit:
                    within_range = other_u
                    break
            if within_range is None:
                for other_setl in all_setls:
                    if other_setl not in player.settlements:
                        could_attack: bool = (player.ai_playstyle is AIPlaystyle.AGGRESSIVE and
                                             unit.health >= other_setl.strength * 2) or \
                                             (player.ai_playstyle is AIPlaystyle.NEUTRAL and
                                              unit.health >= other_setl.strength * 10) or \
                                             (player.ai_playstyle is AIPlaystyle.DEFENSIVE and other_setl.strength == 0)
                        if could_attack:
                            if max(abs(unit.location[0] - other_setl.location[0]),
                                   abs(unit.location[1] - other_setl.location[1])) <= unit.remaining_stamina:
                                within_range = other_setl
                                break
                        else:
                            could_siege: bool = player.ai_playstyle is AIPlaystyle.AGGRESSIVE or \
                                     (player.ai_playstyle is AIPlaystyle.NEUTRAL and unit.health >= other_setl.strength * 2)
                            if could_siege:
                                if max(abs(unit.location[0] - other_setl.location[0]),
                                       abs(unit.location[1] - other_setl.location[1])) <= unit.remaining_stamina:
                                    within_range = other_setl
                                    attack_over_siege = False
                                    break
            if within_range is not None:
                first_resort: (int, int)
                second_resort = within_range.location[0], within_range.location[1] + 1
                third_resort = within_range.location[0], within_range.location[1] - 1
                if within_range.location[0] - unit.location[0] < 0:
                    first_resort = within_range.location[0] + 1, within_range.location[1]
                else:
                    first_resort = within_range.location[0] - 1, within_range.location[1]
                found_valid_loc = False
                for loc in [first_resort, second_resort, third_resort]:
                    if not any(u.location == loc for u in player.units) and \
                            not any(other_u.location == loc for other_u in other_units) and \
                            not any(setl.location == loc for setl in all_setls):
                        unit.location = loc
                        found_valid_loc = True
                        break
                unit.remaining_stamina = 0
                if found_valid_loc:
                    if attack_over_siege:
                        if isinstance(within_range, Unit):
                            unit.sieging = False
                            for p in all_players:
                                for s in p.settlements:
                                    if s.under_siege_by is unit:
                                        s.under_siege_by = None
                            data = attack(unit, within_range)

                            if within_range in all_players[0].units:
                                self.board_ref.overlay.toggle_attack(data)
                            if within_range.health <= 0:
                                for p in all_players:
                                    if within_range in p.units:
                                        p.units.remove(within_range)
                                        break
                            if unit.health <= 0:
                                player.units.remove(unit)
                        else:
                            setl_owner = None
                            for pl in all_players:
                                if within_range in pl.settlements:
                                    setl_owner = pl
                            data = attack_setl(unit, within_range, setl_owner)

                            if within_range in all_players[0].settlements:
                                self.board_ref.overlay.toggle_setl_attack(data)
                            if data.attacker_was_killed:
                                player.units.remove(data.attacker)
                            elif data.setl_was_taken:
                                data.settlement.under_siege_by = None
                                player.settlements.append(data.settlement)
                                setl_owner.settlements.remove(data.settlement)
                    elif not unit.sieging:
                        unit.sieging = True
                        within_range.under_siege_by = unit
                        if within_range in all_players[0].settlements:
                            self.board_ref.overlay.toggle_siege_notif(within_range, player)
            else:
                x_movement = random.randint(-unit.remaining_stamina, unit.remaining_stamina)
                rem_movement = unit.remaining_stamina - abs(x_movement)
                y_movement = random.choice([-rem_movement, rem_movement])
                unit.location = clamp(unit.location[0] + x_movement, 0, 99), clamp(unit.location[1] + y_movement, 0, 89)
                unit.remaining_stamina -= abs(x_movement) + abs(y_movement)
