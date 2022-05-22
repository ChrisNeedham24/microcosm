import math
import typing
from enum import Enum

import pyxel

from calculator import get_setl_totals
from catalogue import get_unlockable_improvements, get_all_unlockable
from models import Settlement, Player, Improvement, Unit, Blessing, ImprovementType, CompletedConstruction, UnitPlan, \
    EconomicStatus, HarvestStatus, Heathen, AttackData, SetlAttackData, Victory, VictoryType


"""
VICTORY!
CONTROLS
PAUSE
DEPLOYMENT! = TUTORIAL = WARNING! = BLESS_NOTIF! = CONSTR_NOTIF! = LEVEL_NOTIF!
BLESSING
STANDARD = CONSTRUCTION = SETL_CLICK
SETTLEMENT = UNIT
ATTACK = SETL_ATTACK = SIEGE_NOTIF
"""

class OverlayType(Enum):
    STANDARD = "STANDARD"
    SETTLEMENT = "SETTLEMENT"
    CONSTRUCTION = "CONSTRUCTION"
    BLESSING = "BLESSING"
    DEPLOYMENT = "DEPLOYMENT"
    UNIT = "UNIT"
    TUTORIAL = "TUTORIAL"
    WARNING = "WARNING"
    BLESS_NOTIF = "BLESS_NOTIF"
    CONSTR_NOTIF = "CONSTR_NOTIF"
    LEVEL_NOTIF = "LEVEL_NOTIF"
    ATTACK = "ATTACK"
    SETL_ATTACK = "SETL_ATTACK"
    SETL_CLICK = "SETL_CLICK"
    SIEGE_NOTIF = "SIEGE_NOTIF"
    PAUSE = "PAUSE"
    CONTROLS = "CONTROLS"
    VICTORY = "VICTORY"


class SettlementAttackType(Enum):
    ATTACK = "ATTACK"
    BESIEGE = "BESIEGE"


class PauseOption(Enum):
    RESUME = "RESUME"
    SAVE = "SAVE"
    CONTROLS = "CONTROLS"
    QUIT = "QUIT"


class Overlay:
    def __init__(self):
        self.showing: typing.List[OverlayType] = []
        self.current_turn: int = 0
        self.current_settlement: typing.Optional[Settlement] = None
        self.current_player: typing.Optional[Player] = None
        self.available_constructions: typing.List[Improvement] = []
        self.available_unit_plans: typing.List[UnitPlan] = []
        self.selected_construction: typing.Optional[typing.Union[Improvement, UnitPlan]] = None
        self.construction_boundaries: typing.Tuple[int, int] = 0, 5
        self.unit_plan_boundaries: typing.Tuple[int, int] = 0, 5
        self.constructing_improvement: bool = True
        self.selected_unit: typing.Optional[typing.Union[Unit, Heathen]] = None
        self.available_blessings: typing.List[Blessing] = []
        self.selected_blessing: typing.Optional[Blessing] = None
        self.blessing_boundaries: typing.Tuple[int, int] = 0, 5
        self.problematic_settlements: typing.List[Settlement] = []
        self.has_no_blessing: bool = False
        self.will_have_negative_wealth = False
        self.completed_blessing: typing.Optional[Blessing] = None
        self.completed_constructions: typing.List[CompletedConstruction] = []
        self.levelled_up_settlements: typing.List[Settlement] = []
        self.attack_data: typing.Optional[AttackData] = None
        self.setl_attack_data: typing.Optional[SetlAttackData] = None
        self.setl_attack_opt: typing.Optional[SettlementAttackType] = None
        self.attacked_settlement: typing.Optional[Settlement] = None
        self.attacked_settlement_owner: typing.Optional[Player] = None
        self.sieged_settlement: typing.Optional[Settlement] = None
        self.sieger_of_settlement: typing.Optional[Player] = None
        self.pause_option: PauseOption = PauseOption.RESUME
        self.current_victory: typing.Optional[Victory] = None

    def display(self):
        pyxel.load("resources/sprites.pyxres")
        if OverlayType.VICTORY in self.showing:
            pyxel.rectb(12, 60, 176, 38, pyxel.COLOR_WHITE)
            pyxel.rect(13, 61, 174, 36, pyxel.COLOR_BLACK)
            if self.current_victory.player is self.current_player:
                beginning = "You have"
                pyxel.text(82, 65, "Victory!", pyxel.COLOR_GREEN)
            else:
                beginning = f"{self.current_victory.player.name} has"
                pyxel.text(82, 65, "Game over!", pyxel.COLOR_RED)

            if self.current_victory.type is VictoryType.ELIMINATION:
                pyxel.text(22, 75, f"{beginning} achieved an ELIMINATION victory.", pyxel.COLOR_RED)
            elif self.current_victory.type is VictoryType.JUBILATION or self.current_victory.type is VictoryType.GLUTTONY:
                pyxel.text(22, 75, f"{beginning} achieved a {self.current_victory.type.value} victory.", pyxel.COLOR_GREEN)
            elif self.current_victory.type is VictoryType.AFFLUENCE:
                pyxel.text(22, 75, f"{beginning} achieved an AFFLUENCE victory.", pyxel.COLOR_YELLOW)
            elif self.current_victory.type is VictoryType.VIGOUR:
                pyxel.text(22, 75, f"{beginning} achieved a VIGOUR victory.", pyxel.COLOR_ORANGE)
            else:
                pyxel.text(22, 75, f"{beginning} achieved a SERENDIPITY victory.", pyxel.COLOR_PURPLE)

            pyxel.text(35, 85, "Press ENTER to return to the menu.", pyxel.COLOR_WHITE)
        elif OverlayType.DEPLOYMENT in self.showing:
            pyxel.rectb(12, 150, 176, 15, pyxel.COLOR_WHITE)
            pyxel.rect(13, 151, 174, 13, pyxel.COLOR_BLACK)
            pyxel.text(15, 153, "Click a quad in the white square to deploy!", pyxel.COLOR_WHITE)
        elif OverlayType.BLESS_NOTIF in self.showing:
            unlocked = get_all_unlockable(self.completed_blessing)
            pyxel.rectb(12, 60, 176, 45 + len(unlocked) * 10, pyxel.COLOR_WHITE)
            pyxel.rect(13, 61, 174, 43 + len(unlocked) * 10, pyxel.COLOR_BLACK)
            pyxel.text(60, 63, "Blessing completed!", pyxel.COLOR_PURPLE)
            pyxel.text(20, 73, self.completed_blessing.name, pyxel.COLOR_WHITE)
            pyxel.text(20, 83, "Unlocks:", pyxel.COLOR_WHITE)
            for idx, imp in enumerate(unlocked):
                pyxel.text(25, 93 + idx * 10, imp.name, pyxel.COLOR_RED)
            pyxel.text(70, 93 + len(unlocked) * 10, "SPACE: Dismiss", pyxel.COLOR_WHITE)
        elif OverlayType.CONSTR_NOTIF in self.showing:
            pyxel.rectb(12, 60, 176, 25 + len(self.completed_constructions) * 20, pyxel.COLOR_WHITE)
            pyxel.rect(13, 61, 174, 23 + len(self.completed_constructions) * 20, pyxel.COLOR_BLACK)
            pluralisation = "s" if len(self.completed_constructions) > 1 else ""
            pyxel.text(60, 63, f"Construction{pluralisation} completed!", pyxel.COLOR_RED)
            for idx, constr in enumerate(self.completed_constructions):
                pyxel.text(20, 73 + idx * 20, constr.settlement.name, pyxel.COLOR_WHITE)
                pyxel.text(25, 83 + idx * 20, constr.construction.name, pyxel.COLOR_RED)
            pyxel.text(70, 73 + len(self.completed_constructions) * 20, "SPACE: Dismiss", pyxel.COLOR_WHITE)
        elif OverlayType.LEVEL_NOTIF in self.showing:
            pyxel.rectb(12, 60, 176, 25 + len(self.levelled_up_settlements) * 20, pyxel.COLOR_WHITE)
            pyxel.rect(13, 61, 174, 23 + len(self.levelled_up_settlements) * 20, pyxel.COLOR_BLACK)
            pluralisation = "s" if len(self.levelled_up_settlements) > 1 else ""
            pyxel.text(60, 63, f"Settlement{pluralisation} level up!", pyxel.COLOR_WHITE)
            for idx, setl in enumerate(self.levelled_up_settlements):
                pyxel.text(20, 73 + idx * 20, setl.name, pyxel.COLOR_WHITE)
                pyxel.text(25, 83 + idx * 20, f"{setl.level - 1} -> {setl.level}", pyxel.COLOR_WHITE)
            pyxel.text(70, 73 + len(self.levelled_up_settlements) * 20, "SPACE: Dismiss", pyxel.COLOR_WHITE)
        elif OverlayType.WARNING in self.showing:
            extension = 0
            if self.will_have_negative_wealth:
                extension += 20
            if self.has_no_blessing:
                extension += 10
            if len(self.problematic_settlements) > 0:
                extension += len(self.problematic_settlements) * 10 + 1
            pyxel.rectb(12, 60, 176, 20 + extension, pyxel.COLOR_WHITE)
            pyxel.rect(13, 61, 174, 18 + extension, pyxel.COLOR_BLACK)
            pyxel.text(85, 63, "Warning!", pyxel.COLOR_WHITE)
            offset = 0
            if self.will_have_negative_wealth:
                pyxel.text(32, 73, "Your treasuries will be depleted!", pyxel.COLOR_YELLOW)
                pyxel.text(20, 83, "Units will be auto-sold to recoup losses.", pyxel.COLOR_WHITE)
                offset += 20
            if self.has_no_blessing:
                pyxel.text(20, 73 + offset, "You are currently undergoing no blessing!", pyxel.COLOR_PURPLE)
                offset += 10
            if len(self.problematic_settlements) > 0:
                pyxel.text(15, 73 + offset, "The below settlements have no construction:", pyxel.COLOR_RED)
                offset += 10
                for setl in self.problematic_settlements:
                    pyxel.text(80, 73 + offset, setl.name, pyxel.COLOR_WHITE)
                    offset += 10
        else:
            if OverlayType.ATTACK in self.showing:
                pyxel.rectb(12, 10, 176, 26, pyxel.COLOR_WHITE)
                pyxel.rect(13, 11, 174, 24, pyxel.COLOR_BLACK)
                att_name = self.attack_data.attacker.plan.name
                att_dmg = round(self.attack_data.damage_to_attacker)
                def_name = self.attack_data.defender.plan.name
                def_dmg = round(self.attack_data.damage_to_defender)
                if self.attack_data.attacker_was_killed and self.attack_data.player_attack:
                    pyxel.text(35, 15, f"Your {att_name} (-{att_dmg}) was killed by", pyxel.COLOR_WHITE)
                elif self.attack_data.defender_was_killed and not self.attack_data.player_attack:
                    pyxel.text(35, 15, f"Your {def_name} (-{def_dmg}) was killed by", pyxel.COLOR_WHITE)
                elif self.attack_data.attacker_was_killed and not self.attack_data.player_attack:
                    pyxel.text(50, 15, f"Your {def_name} (-{def_dmg}) killed", pyxel.COLOR_WHITE)
                elif self.attack_data.defender_was_killed and self.attack_data.player_attack:
                    pyxel.text(50, 15, f"Your {att_name} (-{att_dmg}) killed", pyxel.COLOR_WHITE)
                elif self.attack_data.player_attack:
                    pyxel.text(46, 15, f"Your {att_name} (-{att_dmg}) attacked", pyxel.COLOR_WHITE)
                else:
                    pyxel.text(32, 15, f"Your {def_name} (-{def_dmg}) was attacked by", pyxel.COLOR_WHITE)
                pyxel.text(72, 25, f"a {def_name if self.attack_data.player_attack else att_name} "
                                   f"(-{def_dmg if self.attack_data.player_attack else att_dmg})", pyxel.COLOR_WHITE)
            if OverlayType.SETL_ATTACK in self.showing:
                pyxel.rectb(12, 10, 176, 26, pyxel.COLOR_WHITE)
                pyxel.rect(13, 11, 174, 24, pyxel.COLOR_BLACK)
                att_name = self.setl_attack_data.attacker.plan.name
                att_dmg = round(self.setl_attack_data.damage_to_attacker)
                setl_name = self.setl_attack_data.settlement.name
                setl_dmg = round(self.setl_attack_data.damage_to_setl)
                if self.setl_attack_data.attacker_was_killed:
                    pyxel.text(35, 15, f"Your {att_name} (-{att_dmg}) was killed by", pyxel.COLOR_WHITE)
                elif self.setl_attack_data.setl_was_taken and self.setl_attack_data.player_attack:
                    pyxel.text(50, 15, f"Your {att_name} (-{att_dmg}) sacked", pyxel.COLOR_WHITE)
                elif self.setl_attack_data.setl_was_taken:
                    pyxel.text(70, 15, f"A {att_name} sacked", pyxel.COLOR_WHITE)
                elif self.setl_attack_data.player_attack:
                    pyxel.text(46, 15, f"Your {att_name} (-{att_dmg}) attacked", pyxel.COLOR_WHITE)
                else:
                    pyxel.text(54, 15, f"A {att_name} (-{att_dmg}) attacked", pyxel.COLOR_WHITE)
                pyxel.text(72, 25, f"{setl_name} (-{setl_dmg})", self.setl_attack_data.setl_owner.colour)
            if OverlayType.SIEGE_NOTIF in self.showing:
                pyxel.rectb(12, 10, 176, 16, pyxel.COLOR_WHITE)
                pyxel.rect(13, 11, 174, 14, pyxel.COLOR_BLACK)
                att_name = self.sieger_of_settlement.name
                setl_name = self.sieged_settlement.name
                pyxel.text(22, 15, f"{setl_name} was placed under siege by {att_name}", pyxel.COLOR_RED)
            if OverlayType.SETTLEMENT in self.showing:
                pyxel.rectb(12, 10, 176, 16, pyxel.COLOR_WHITE)
                pyxel.rect(13, 11, 174, 14, pyxel.COLOR_BLACK)
                pyxel.text(20, 14, f"{self.current_settlement.name} ({self.current_settlement.level})",
                           self.current_player.colour)
                pyxel.blt(80, 12, 0, 0, 28, 8, 8)
                pyxel.text(90, 14, str(self.current_settlement.strength), pyxel.COLOR_WHITE)
                satisfaction_u = 8 if self.current_settlement.satisfaction >= 50 else 16
                pyxel.blt(105, 12, 0, satisfaction_u, 28, 8, 8)
                pyxel.text(115, 14, str(round(self.current_settlement.satisfaction)), pyxel.COLOR_WHITE)

                total_wealth, total_harvest, total_zeal, total_fortune = get_setl_totals(self.current_settlement,
                                                                                         strict=True)

                pyxel.text(138, 14, str(round(total_wealth)), pyxel.COLOR_YELLOW)
                pyxel.text(150, 14, str(round(total_harvest)), pyxel.COLOR_GREEN)
                pyxel.text(162, 14, str(round(total_zeal)), pyxel.COLOR_RED)
                pyxel.text(174, 14, str(round(total_fortune)), pyxel.COLOR_PURPLE)

                y_offset = 0
                if self.current_settlement.current_work is not None and \
                    self.current_player.wealth >= \
                    (self.current_settlement.current_work.construction.cost -
                     self.current_settlement.current_work.zeal_consumed):
                    y_offset = 10
                pyxel.rectb(12, 130 - y_offset, 176, 40 + y_offset, pyxel.COLOR_WHITE)
                pyxel.rect(13, 131 - y_offset, 174, 38 + y_offset, pyxel.COLOR_BLACK)
                pyxel.line(100, 130 - y_offset, 100, 168, pyxel.COLOR_WHITE)
                pyxel.text(20, 134 - y_offset, "Construction", pyxel.COLOR_RED)
                if self.current_settlement.current_work is not None:
                    current_work = self.current_settlement.current_work
                    remaining_work = current_work.construction.cost - current_work.zeal_consumed
                    total_zeal = max(sum(quad.zeal for quad in self.current_settlement.quads) +
                                                sum(imp.effect.zeal for imp in self.current_settlement.improvements), 0.5)
                    total_zeal += (self.current_settlement.level - 1) * 0.25 * total_zeal
                    remaining_turns = math.ceil(remaining_work / total_zeal)
                    pyxel.text(20, 145 - y_offset, current_work.construction.name, pyxel.COLOR_WHITE)
                    pyxel.text(20, 155 - y_offset, f"{remaining_turns} turns remaining", pyxel.COLOR_WHITE)
                    if self.current_player.wealth >= remaining_work:
                        pyxel.blt(20, 153, 0, 0, 52, 8, 8)
                        pyxel.text(30, 155, "Buyout:", pyxel.COLOR_WHITE)
                        pyxel.blt(60, 153, 0, 0, 44, 8, 8)
                        pyxel.text(70, 155, str(round(remaining_work)), pyxel.COLOR_WHITE)
                        pyxel.text(87, 155, "(B)", pyxel.COLOR_WHITE)
                else:
                    pyxel.text(20, 145 - y_offset, "None", pyxel.COLOR_RED)
                    pyxel.text(20, 155 - y_offset, "Press C to add one!", pyxel.COLOR_WHITE)
                pyxel.text(110, 134 - y_offset, "Garrison", pyxel.COLOR_RED)
                if len(self.current_settlement.garrison) > 0:
                    pluralisation = "s" if len(self.current_settlement.garrison) > 1 else ""
                    pyxel.text(110, 145 - y_offset, f"{len(self.current_settlement.garrison)} unit{pluralisation}",
                               pyxel.COLOR_WHITE)
                    pyxel.text(110, 155 - y_offset, "Press D to deploy!", pyxel.COLOR_WHITE)
                else:
                    pyxel.text(110, 145 - y_offset, "No units.", pyxel.COLOR_RED)
            if OverlayType.UNIT in self.showing:
                pyxel.rectb(12, 110, 56, 60, pyxel.COLOR_WHITE)
                pyxel.rect(13, 111, 54, 58, pyxel.COLOR_BLACK)
                pyxel.text(20, 114, self.selected_unit.plan.name, pyxel.COLOR_WHITE)
                if self.selected_unit.plan.can_settle:
                    pyxel.blt(55, 113, 0, 24, 36, 8, 8)
                if self.selected_unit.sieging and self.selected_unit in self.current_player.units:
                    pyxel.blt(55, 113, 0, 32, 36, 8, 8)
                    pyxel.rectb(12, 10, 176, 16, pyxel.COLOR_WHITE)
                    pyxel.rect(13, 11, 174, 14, pyxel.COLOR_BLACK)
                    pyxel.text(18, 14, "Remember: the siege will end if you move!", pyxel.COLOR_RED)
                pyxel.blt(20, 120, 0, 8, 36, 8, 8)
                pyxel.text(30, 122, str(self.selected_unit.health), pyxel.COLOR_WHITE)
                pyxel.blt(20, 130, 0, 0, 36, 8, 8)
                pyxel.text(30, 132, str(self.selected_unit.plan.power), pyxel.COLOR_WHITE)
                pyxel.blt(20, 140, 0, 16, 36, 8, 8)
                pyxel.text(30, 142, f"{self.selected_unit.remaining_stamina}/{self.selected_unit.plan.total_stamina}",
                           pyxel.COLOR_WHITE)
                pyxel.blt(20, 150, 0, 0, 44, 8, 8)
                pyxel.text(30, 152, f"{self.selected_unit.plan.cost} (-{round(self.selected_unit.plan.cost / 25)}/T)",
                           pyxel.COLOR_WHITE)
                pyxel.blt(20, 160, 0, 8, 52, 8, 8)
                pyxel.text(30, 162, "Disb. (D)", pyxel.COLOR_RED)
            if OverlayType.CONSTRUCTION in self.showing:
                pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
                pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
                pyxel.text(55, 25, "Available constructions", pyxel.COLOR_RED)
                total_zeal = 0
                total_zeal += sum(quad.zeal for quad in self.current_settlement.quads)
                total_zeal += sum(imp.effect.zeal for imp in self.current_settlement.improvements)
                total_zeal = max(0.5, total_zeal) + (self.current_settlement.level - 1) * 0.25 * total_zeal
                if self.constructing_improvement:
                    for idx, construction in enumerate(self.available_constructions):
                        if self.construction_boundaries[0] <= idx <= self.construction_boundaries[1]:
                            adj_idx = idx - self.construction_boundaries[0]
                            pyxel.text(30, 35 + adj_idx * 18,
                                       f"{construction.name} ({math.ceil(construction.cost / total_zeal)})",
                                       pyxel.COLOR_WHITE)
                            pyxel.text(150, 35 + adj_idx * 18, "Build",
                                       pyxel.COLOR_RED if self.selected_construction is construction else pyxel.COLOR_WHITE)
                            effects = 0
                            if construction.effect.wealth != 0:
                                sign = "+" if construction.effect.wealth > 0 else "-"
                                pyxel.text(30 + effects * 25, 42 + adj_idx * 18,
                                           f"{sign}{abs(construction.effect.wealth)}", pyxel.COLOR_YELLOW)
                                effects += 1
                            if construction.effect.harvest != 0:
                                sign = "+" if construction.effect.harvest > 0 else "-"
                                pyxel.text(30 + effects * 25, 42 + adj_idx * 18,
                                           f"{sign}{abs(construction.effect.harvest)}", pyxel.COLOR_GREEN)
                                effects += 1
                            if construction.effect.zeal != 0:
                                sign = "+" if construction.effect.zeal > 0 else "-"
                                pyxel.text(30 + effects * 25, 42 + adj_idx * 18,
                                           f"{sign}{abs(construction.effect.zeal)}", pyxel.COLOR_RED)
                                effects += 1
                            if construction.effect.fortune != 0:
                                sign = "+" if construction.effect.fortune > 0 else "-"
                                pyxel.text(30 + effects * 25, 42 + adj_idx * 18,
                                           f"{sign}{abs(construction.effect.fortune)}", pyxel.COLOR_PURPLE)
                                effects += 1
                            if construction.effect.strength != 0:
                                sign = "+" if construction.effect.strength > 0 else "-"
                                pyxel.blt(30 + effects * 25, 42 + adj_idx * 18, 0, 0, 28, 8, 8)
                                pyxel.text(40 + effects * 25, 42 + adj_idx * 18,
                                           f"{sign}{abs(construction.effect.strength)}", pyxel.COLOR_WHITE)
                                effects += 1
                            if construction.effect.satisfaction != 0:
                                sign = "+" if construction.effect.satisfaction > 0 else "-"
                                satisfaction_u = 8 if construction.effect.satisfaction >= 0 else 16
                                pyxel.blt(30 + effects * 25, 42 + adj_idx * 18, 0, satisfaction_u, 28, 8, 8)
                                pyxel.text(40 + effects * 25, 42 + adj_idx * 18,
                                           f"{sign}{abs(construction.effect.satisfaction)}", pyxel.COLOR_WHITE)
                else:
                    for idx, unit_plan in enumerate(self.available_unit_plans):
                        if self.unit_plan_boundaries[0] <= idx <= self.unit_plan_boundaries[1]:
                            adj_idx = idx - self.unit_plan_boundaries[0]
                            pyxel.text(30, 35 + adj_idx * 18,
                                       f"{unit_plan.name} ({math.ceil(unit_plan.cost / total_zeal)})",
                                       pyxel.COLOR_WHITE)
                            pyxel.text(146, 35 + adj_idx * 18, "Recruit",
                                       pyxel.COLOR_RED if self.selected_construction is unit_plan else pyxel.COLOR_WHITE)
                            pyxel.blt(30, 42 + adj_idx * 18, 0, 8, 36, 8, 8)
                            pyxel.text(45, 42 + adj_idx * 18, str(unit_plan.max_health), pyxel.COLOR_WHITE)
                            pyxel.blt(60, 42 + adj_idx * 18, 0, 0, 36, 8, 8)
                            pyxel.text(75, 42 + adj_idx * 18, str(unit_plan.power), pyxel.COLOR_WHITE)
                            pyxel.blt(90, 42 + adj_idx * 18, 0, 16, 36, 8, 8)
                            pyxel.text(105, 42 + adj_idx * 18, str(unit_plan.total_stamina), pyxel.COLOR_WHITE)
                            if unit_plan.can_settle:
                                pyxel.text(115, 42 + adj_idx * 18, "-1 LVL", pyxel.COLOR_WHITE)
                pyxel.text(90, 150, "Cancel",
                           pyxel.COLOR_RED if self.selected_construction is None else pyxel.COLOR_WHITE)
                if self.constructing_improvement:
                    pyxel.text(140, 150, "Units ->", pyxel.COLOR_WHITE)
                else:
                    pyxel.text(25, 150, "<- Improvements", pyxel.COLOR_WHITE)
            if OverlayType.STANDARD in self.showing:
                pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
                pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
                pyxel.text(90, 30, f"Turn {self.current_turn}", pyxel.COLOR_WHITE)
                pyxel.text(30, 40, "Blessing", pyxel.COLOR_PURPLE)
                if self.current_player.ongoing_blessing is not None:
                    ong_blessing = self.current_player.ongoing_blessing
                    remaining_work = ong_blessing.blessing.cost - ong_blessing.fortune_consumed
                    total_fortune = 0
                    for setl in self.current_player.settlements:
                        fortune_to_add = 0
                        fortune_to_add += sum(quad.fortune for quad in setl.quads)
                        fortune_to_add += sum(imp.effect.fortune for imp in setl.improvements)
                        fortune_to_add += (setl.level - 1) * 0.25 * fortune_to_add
                        total_fortune += fortune_to_add
                    total_fortune = max(0.5, total_fortune)
                    remaining_turns = math.ceil(remaining_work / total_fortune)
                    pyxel.text(30, 50, ong_blessing.blessing.name, pyxel.COLOR_WHITE)
                    pyxel.text(30, 60, f"{remaining_turns} turns remaining", pyxel.COLOR_WHITE)
                else:
                    pyxel.text(30, 50, "None", pyxel.COLOR_RED)
                    pyxel.text(30, 60, "Press F to add one!", pyxel.COLOR_WHITE)
                pyxel.text(30, 80, "Wealth", pyxel.COLOR_YELLOW)
                wealth_per_turn = 0
                for setl in self.current_player.settlements:
                    wealth_to_add = 0
                    wealth_to_add += sum(quad.wealth for quad in setl.quads)
                    wealth_to_add += sum(imp.effect.wealth for imp in setl.improvements)
                    wealth_to_add += (setl.level - 1) * 0.25 * wealth_to_add
                    if setl.economic_status is EconomicStatus.RECESSION:
                        wealth_to_add = 0
                    elif setl.economic_status is EconomicStatus.BOOM:
                        wealth_to_add *= 1.5
                    wealth_per_turn += wealth_to_add
                for unit in self.current_player.units:
                    if not unit.garrisoned:
                        wealth_per_turn -= unit.plan.cost / 25
                sign = "+" if wealth_per_turn > 0 else "-"
                pyxel.text(30, 90,
                           f"{round(self.current_player.wealth)} ({sign}{abs(round(wealth_per_turn, 2))})",
                           pyxel.COLOR_WHITE)
            if OverlayType.SETL_CLICK in self.showing:
                pyxel.rectb(50, 60, 100, 70, pyxel.COLOR_WHITE)
                pyxel.rect(51, 61, 98, 68, pyxel.COLOR_BLACK)
                name_len = len(self.attacked_settlement.name)
                x_offset = 11 - name_len
                pyxel.text(82 + x_offset, 70, str(self.attacked_settlement.name), self.attacked_settlement_owner.colour)
                pyxel.blt(90, 78, 0, 0, 28, 8, 8)
                pyxel.text(100, 80, str(self.attacked_settlement.strength), pyxel.COLOR_WHITE)
                pyxel.text(68, 95, "Attack",
                           pyxel.COLOR_RED
                           if self.setl_attack_opt is SettlementAttackType.ATTACK else pyxel.COLOR_WHITE)
                pyxel.text(110, 95, "Besiege",
                           pyxel.COLOR_RED
                           if self.setl_attack_opt is SettlementAttackType.BESIEGE else pyxel.COLOR_WHITE)
                pyxel.text(90, 115, "Cancel", pyxel.COLOR_RED if self.setl_attack_opt is None else pyxel.COLOR_WHITE)
            if OverlayType.BLESSING in self.showing:
                pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
                pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
                pyxel.text(65, 25, "Available blessings", pyxel.COLOR_PURPLE)
                total_fortune = 0
                for setl in self.current_player.settlements:
                    fortune_to_add = 0
                    fortune_to_add += sum(quad.fortune for quad in setl.quads)
                    fortune_to_add += sum(imp.effect.fortune for imp in setl.improvements)
                    fortune_to_add += (setl.level - 1) * 0.25 * fortune_to_add
                    total_fortune += fortune_to_add
                total_fortune = max(0.5, total_fortune)
                for idx, blessing in enumerate(self.available_blessings):
                    if self.blessing_boundaries[0] <= idx <= self.blessing_boundaries[1]:
                        adj_idx = idx - self.blessing_boundaries[0]
                        pyxel.text(30, 35 + adj_idx * 18,
                                   f"{blessing.name} ({math.ceil(blessing.cost / total_fortune)})", pyxel.COLOR_WHITE)
                        pyxel.text(145, 35 + adj_idx * 18, "Undergo",
                                   pyxel.COLOR_RED if self.selected_blessing is blessing else pyxel.COLOR_WHITE)
                        imps = get_unlockable_improvements(blessing)
                        pyxel.text(30, 42 + adj_idx * 18, "Unlocks:", pyxel.COLOR_WHITE)
                        types_unlockable: typing.List[ImprovementType] = []
                        if len(imps) > 0:
                            for imp in imps:
                                if imp.effect.wealth > 0:
                                    types_unlockable.append(ImprovementType.ECONOMICAL)
                                if imp.effect.harvest > 0:
                                    types_unlockable.append(ImprovementType.BOUNTIFUL)
                                if imp.effect.zeal > 0:
                                    types_unlockable.append(ImprovementType.INDUSTRIAL)
                                if imp.effect.fortune > 0:
                                    types_unlockable.append(ImprovementType.MAGICAL)
                                if imp.effect.strength > 0:
                                    types_unlockable.append(ImprovementType.INTIMIDATORY)
                                if imp.effect.satisfaction > 0:
                                    types_unlockable.append(ImprovementType.PANDERING)
                            if len(types_unlockable) > 0:
                                for type_idx, unl_type in enumerate(set(types_unlockable)):
                                    uv_coords: (int, int) = 0, 44
                                    if unl_type is ImprovementType.BOUNTIFUL:
                                        uv_coords = 8, 44
                                    elif unl_type is ImprovementType.INDUSTRIAL:
                                        uv_coords = 16, 44
                                    elif unl_type is ImprovementType.MAGICAL:
                                        uv_coords = 24, 44
                                    elif unl_type is ImprovementType.INTIMIDATORY:
                                        uv_coords = 0, 28
                                    elif unl_type is ImprovementType.PANDERING:
                                        uv_coords = 8, 28
                                    pyxel.blt(65 + type_idx * 10, 41 + adj_idx * 18, 0, uv_coords[0], uv_coords[1], 8, 8)
                            else:
                                pyxel.text(65, 41 + adj_idx * 18, "victory", pyxel.COLOR_GREEN)
                        else:
                            pyxel.text(65, 41 + adj_idx * 18, "victory", pyxel.COLOR_GREEN)
                pyxel.text(90, 150, "Cancel", pyxel.COLOR_RED if self.selected_blessing is None else pyxel.COLOR_WHITE)
            if OverlayType.TUTORIAL in self.showing:
                pyxel.rectb(8, 140, 184, 25, pyxel.COLOR_WHITE)
                pyxel.rect(9, 141, 182, 23, pyxel.COLOR_BLACK)
                pyxel.text(60, 143, "Welcome to Microcosm!", pyxel.COLOR_WHITE)
                pyxel.text(12, 153, "Click a quad to found your first settlement.", pyxel.COLOR_WHITE)
            if OverlayType.PAUSE in self.showing:
                pyxel.rectb(52, 60, 96, 63, pyxel.COLOR_WHITE)
                pyxel.rect(53, 61, 94, 61, pyxel.COLOR_BLACK)
                pyxel.text(80, 68, "Game paused", pyxel.COLOR_WHITE)
                pyxel.text(88, 80, "Resume", pyxel.COLOR_RED if self.pause_option is PauseOption.RESUME else pyxel.COLOR_WHITE)
                pyxel.text(90, 90, "Save", pyxel.COLOR_RED if self.pause_option is PauseOption.SAVE else pyxel.COLOR_WHITE)
                pyxel.text(84, 100, "Controls",
                           pyxel.COLOR_RED if self.pause_option is PauseOption.CONTROLS else pyxel.COLOR_WHITE)
                pyxel.text(90, 110, "Quit",
                           pyxel.COLOR_RED if self.pause_option is PauseOption.QUIT else pyxel.COLOR_WHITE)
            if OverlayType.CONTROLS in self.showing:
                pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
                pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
                pyxel.text(85, 30, "Controls", pyxel.COLOR_WHITE)
                pyxel.text(30, 45, "ARROWS", pyxel.COLOR_WHITE)
                pyxel.text(65, 45, "Navigate menus/pan map", pyxel.COLOR_WHITE)
                pyxel.text(30, 55, "R CLICK", pyxel.COLOR_WHITE)
                pyxel.text(65, 55, "Show quad yield", pyxel.COLOR_WHITE)
                pyxel.text(30, 65, "L CLICK", pyxel.COLOR_WHITE)
                pyxel.text(65, 65, "Move/select/attack units", pyxel.COLOR_WHITE)
                pyxel.text(30, 75, "C", pyxel.COLOR_WHITE)
                pyxel.text(65, 75, "Add/change construction", pyxel.COLOR_WHITE)
                pyxel.text(30, 85, "F", pyxel.COLOR_WHITE)
                pyxel.text(65, 85, "Add/change blessing", pyxel.COLOR_WHITE)
                pyxel.text(30, 95, "D", pyxel.COLOR_WHITE)
                pyxel.text(65, 95, "Deploy/disband unit", pyxel.COLOR_WHITE)
                pyxel.text(30, 105, "N", pyxel.COLOR_WHITE)
                pyxel.text(65, 105, "Next song", pyxel.COLOR_WHITE)
                pyxel.text(30, 115, "B", pyxel.COLOR_WHITE)
                pyxel.text(65, 115, "Buyout construction", pyxel.COLOR_WHITE)
                pyxel.text(56, 150, "Press SPACE to go back.", pyxel.COLOR_WHITE)

    def toggle_standard(self, turn: int):
        if OverlayType.STANDARD in self.showing:
            self.showing.remove(OverlayType.STANDARD)
        elif not self.is_tutorial() and not self.is_lvl_notif() and not self.is_constr_notif() and \
                not self.is_bless_notif() and not self.is_deployment() and not self.is_warning() and \
                not self.is_pause() and not self.is_controls() and not self.is_victory() and not self.is_constructing():
            self.showing.append(OverlayType.STANDARD)
            self.current_turn = turn

    def toggle_construction(self, available_constructions: typing.List[Improvement],
                            available_unit_plans: typing.List[UnitPlan]):
        if OverlayType.CONSTRUCTION in self.showing:
            self.showing.remove(OverlayType.CONSTRUCTION)
        elif not self.is_standard() and not self.is_blessing() and not self.is_lvl_notif() and \
                not self.is_constr_notif() and not self.is_bless_notif() and not self.is_warning() and \
                not self.is_deployment() and not self.is_pause() and not self.is_controls() and not self.is_victory():
            self.showing.append(OverlayType.CONSTRUCTION)
            self.available_constructions = available_constructions
            self.available_unit_plans = available_unit_plans
            if len(available_constructions) > 0:
                self.constructing_improvement = True
                self.selected_construction = self.available_constructions[0]
                self.construction_boundaries = 0, 5
            else:
                self.constructing_improvement = False
                self.selected_construction = self.available_unit_plans[0]
                self.unit_plan_boundaries = 0, 5

    def navigate_constructions(self, down: bool):
        list_to_use = self.available_constructions if self.constructing_improvement else self.available_unit_plans
        if down and self.selected_construction is not None:
            current_index = list_to_use.index(self.selected_construction)
            if current_index != len(list_to_use) - 1:
                self.selected_construction = list_to_use[current_index + 1]
                if current_index == self.construction_boundaries[1]:
                    self.construction_boundaries = \
                        self.construction_boundaries[0] + 1, self.construction_boundaries[1] + 1
            else:
                self.selected_construction = None
        elif not down:
            if self.selected_construction is None:
                self.selected_construction = list_to_use[len(list_to_use) - 1]
            else:
                current_index = list_to_use.index(self.selected_construction)
                if current_index != 0:
                    self.selected_construction = list_to_use[current_index - 1]
                    if current_index == self.construction_boundaries[0]:
                        self.construction_boundaries = \
                            self.construction_boundaries[0] - 1, self.construction_boundaries[1] - 1

    def is_constructing(self) -> bool:
        return OverlayType.CONSTRUCTION in self.showing

    def toggle_blessing(self, available_blessings: typing.List[Blessing]):
        if OverlayType.BLESSING in self.showing:
            self.showing.remove(OverlayType.BLESSING)
        elif not self.is_lvl_notif() and not self.is_constr_notif() and not self.is_bless_notif() and \
                not self.is_deployment() and not self.is_warning() and not self.is_pause() and \
                not self.is_controls() and not self.is_victory():
            self.showing.append(OverlayType.BLESSING)
            self.available_blessings = available_blessings
            self.selected_blessing = self.available_blessings[0]
            self.blessing_boundaries = 0, 5

    def navigate_blessings(self, down: bool):
        if down and self.selected_blessing is not None:
            current_index = self.available_blessings.index(self.selected_blessing)
            if current_index != len(self.available_blessings) - 1:
                self.selected_blessing = self.available_blessings[current_index + 1]
                if current_index == self.blessing_boundaries[1]:
                    self.blessing_boundaries = self.blessing_boundaries[0] + 1, self.blessing_boundaries[1] + 1
            else:
                self.selected_blessing = None
        elif not down:
            if self.selected_blessing is None:
                self.selected_blessing = self.available_blessings[len(self.available_blessings) - 1]
            else:
                current_index = self.available_blessings.index(self.selected_blessing)
                if current_index != 0:
                    self.selected_blessing = self.available_blessings[current_index - 1]
                    if current_index == self.blessing_boundaries[0]:
                        self.blessing_boundaries = self.blessing_boundaries[0] - 1, self.blessing_boundaries[1] - 1

    def is_standard(self) -> bool:
        return OverlayType.STANDARD in self.showing

    def is_blessing(self) -> bool:
        return OverlayType.BLESSING in self.showing

    def toggle_settlement(self, settlement: typing.Optional[Settlement], player: Player):
        if OverlayType.SETTLEMENT in self.showing:
            self.showing.remove(OverlayType.SETTLEMENT)
        elif not self.is_unit() and not self.is_standard() and not self.is_setl_click() and not self.is_blessing() and \
                 not self.is_lvl_notif() and not self.is_constr_notif() and not self.is_deployment() and \
                 not self.is_warning() and not self.is_bless_notif() and not self.is_pause() and \
                 not self.is_controls() and not self.is_victory():
            self.showing.append(OverlayType.SETTLEMENT)
            self.current_settlement = settlement
            self.current_player = player

    def update_settlement(self, settlement: Settlement):
        self.current_settlement = settlement

    def update_unit(self, unit: Unit):
        self.selected_unit = unit

    def toggle_deployment(self):
        if OverlayType.DEPLOYMENT in self.showing:
            self.showing.remove(OverlayType.DEPLOYMENT)
        elif not self.is_warning() and not self.is_bless_notif() and not self.is_constr_notif() and \
                not self.is_lvl_notif() and not self.is_pause() and not self.is_controls() and not self.is_victory():
            self.showing.append(OverlayType.DEPLOYMENT)

    def is_deployment(self):
        return OverlayType.DEPLOYMENT in self.showing

    def toggle_unit(self, unit: typing.Optional[typing.Union[Unit, Heathen]]):
        if OverlayType.UNIT in self.showing:
            self.showing.remove(OverlayType.UNIT)
        elif not self.is_setl() and not self.is_standard() and not self.is_setl_click() and not self.is_blessing() and \
                 not self.is_lvl_notif() and not self.is_constr_notif() and not self.is_deployment() and \
                 not self.is_warning() and not self.is_bless_notif() and not self.is_pause() and \
                 not self.is_controls() and not self.is_victory():
            self.showing.append(OverlayType.UNIT)
            self.selected_unit = unit

    def toggle_tutorial(self):
        if OverlayType.TUTORIAL in self.showing:
            self.showing.remove(OverlayType.TUTORIAL)
        else:
            self.showing.append(OverlayType.TUTORIAL)

    def is_tutorial(self) -> bool:
        return OverlayType.TUTORIAL in self.showing

    def update_turn(self, turn: int):
        self.current_turn = turn

    def is_unit(self):
        return OverlayType.UNIT in self.showing

    def can_iter_settlements_units(self) -> bool:
        return not self.is_victory() and not self.is_controls() and not self.is_pause() and \
            not self.is_deployment() and not self.is_warning() and not self.is_bless_notif() and \
               not self.is_constr_notif() and not self.is_lvl_notif() and not self.is_blessing() and \
            not self.is_standard() and not self.is_constructing() and not self.is_setl_click()

    def is_setl(self):
        return OverlayType.SETTLEMENT in self.showing

    def toggle_warning(self, settlements: typing.List[Settlement], no_blessing: bool, will_have_negative_wealth: bool):
        if OverlayType.WARNING in self.showing:
            self.showing.remove(OverlayType.WARNING)
        else:
            self.showing.append(OverlayType.WARNING)
            self.problematic_settlements = settlements
            self.has_no_blessing = no_blessing
            self.will_have_negative_wealth = will_have_negative_wealth

    def is_warning(self):
        return OverlayType.WARNING in self.showing

    def remove_warning_if_possible(self):
        if OverlayType.WARNING in self.showing:
            self.showing.remove(OverlayType.WARNING)

    def toggle_blessing_notification(self, blessing: typing.Optional[Blessing]):
        if OverlayType.BLESS_NOTIF in self.showing:
            self.showing.remove(OverlayType.BLESS_NOTIF)
        else:
            self.showing.append(OverlayType.BLESS_NOTIF)
            self.completed_blessing = blessing

    def is_bless_notif(self):
        return OverlayType.BLESS_NOTIF in self.showing

    def toggle_construction_notification(self, constructions: typing.List[CompletedConstruction]):
        if OverlayType.CONSTR_NOTIF in self.showing:
            self.showing.remove(OverlayType.CONSTR_NOTIF)
        else:
            self.showing.append(OverlayType.CONSTR_NOTIF)
            self.completed_constructions = constructions

    def is_constr_notif(self):
        return OverlayType.CONSTR_NOTIF in self.showing

    def toggle_level_up_notification(self, settlements: typing.List[Settlement]):
        if OverlayType.LEVEL_NOTIF in self.showing:
            self.showing.remove(OverlayType.LEVEL_NOTIF)
        else:
            self.showing.append(OverlayType.LEVEL_NOTIF)
            self.levelled_up_settlements = settlements

    def is_lvl_notif(self):
        return OverlayType.LEVEL_NOTIF in self.showing

    def toggle_attack(self, attack_data: typing.Optional[AttackData]):
        if OverlayType.ATTACK in self.showing:
            if attack_data is None:
                self.showing.remove(OverlayType.ATTACK)
            else:
                self.attack_data = attack_data
        else:
            self.showing.append(OverlayType.ATTACK)
            self.attack_data = attack_data

    def is_attack(self):
        return OverlayType.ATTACK in self.showing

    def toggle_setl_attack(self, attack_data: typing.Optional[SetlAttackData]):
        if OverlayType.SETL_ATTACK in self.showing:
            if attack_data is None:
                self.showing.remove(OverlayType.SETL_ATTACK)
            else:
                self.setl_attack_data = attack_data
        else:
            self.showing.append(OverlayType.SETL_ATTACK)
            self.setl_attack_data = attack_data

    def is_setl_attack(self):
        return OverlayType.SETL_ATTACK in self.showing

    def toggle_siege_notif(self, sieged: typing.Optional[Settlement], sieger: typing.Optional[Player]):
        if OverlayType.SIEGE_NOTIF in self.showing:
            self.showing.remove(OverlayType.SIEGE_NOTIF)
        else:
            self.showing.append(OverlayType.SIEGE_NOTIF)
            self.sieged_settlement = sieged
            self.sieger_of_settlement = sieger

    def is_siege_notif(self):
        return OverlayType.SIEGE_NOTIF in self.showing

    def toggle_victory(self, victory: Victory):
        self.showing.append(OverlayType.VICTORY)
        self.current_victory = victory

    def is_victory(self):
        return OverlayType.VICTORY in self.showing

    def toggle_setl_click(self, att_setl: typing.Optional[Settlement], owner: typing.Optional[Player]):
        if OverlayType.SETL_CLICK in self.showing:
            self.showing.remove(OverlayType.SETL_CLICK)
        elif not self.is_standard() and not self.is_constructing() and not self.is_blessing() and \
                not self.is_deployment() and not self.is_tutorial() and not self.is_warning() and \
                not self.is_bless_notif() and not self.is_constr_notif() and not self.is_lvl_notif() and \
                not self.is_pause() and not self.is_controls() and not self.is_victory():
            self.showing.append(OverlayType.SETL_CLICK)
            self.setl_attack_opt = SettlementAttackType.ATTACK
            self.attacked_settlement = att_setl
            self.attacked_settlement_owner = owner

    def navigate_setl_click(self, left: bool = False, right: bool = False, up: bool = False, down: bool = False):
        if down:
            self.setl_attack_opt = None
        elif up or left:
            self.setl_attack_opt = SettlementAttackType.ATTACK
        elif right:
            self.setl_attack_opt = SettlementAttackType.BESIEGE

    def is_setl_click(self) -> bool:
        return OverlayType.SETL_CLICK in self.showing

    def toggle_pause(self):
        if OverlayType.PAUSE in self.showing:
            self.showing.remove(OverlayType.PAUSE)
        elif not self.is_victory():
            self.showing.append(OverlayType.PAUSE)
            self.pause_option = PauseOption.RESUME

    def navigate_pause(self, down: bool):
        if down:
            if self.pause_option is PauseOption.RESUME:
                self.pause_option = PauseOption.SAVE
            elif self.pause_option is PauseOption.SAVE:
                self.pause_option = PauseOption.CONTROLS
            elif self.pause_option is PauseOption.CONTROLS:
                self.pause_option = PauseOption.QUIT
        else:
            if self.pause_option is PauseOption.SAVE:
                self.pause_option = PauseOption.RESUME
            elif self.pause_option is PauseOption.CONTROLS:
                self.pause_option = PauseOption.SAVE
            elif self.pause_option is PauseOption.QUIT:
                self.pause_option = PauseOption.CONTROLS

    def is_pause(self) -> bool:
        return OverlayType.PAUSE in self.showing

    def toggle_controls(self):
        if OverlayType.CONTROLS in self.showing:
            self.showing.remove(OverlayType.CONTROLS)
        elif not self.is_victory():
            self.showing.append(OverlayType.CONTROLS)

    def is_controls(self) -> bool:
        return OverlayType.CONTROLS in self.showing
