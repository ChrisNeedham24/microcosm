import math
import typing
from enum import Enum

import pyxel

from catalogue import get_unlockable_improvements
from models import Settlement, Player, Improvement, Unit, Blessing, ImprovementType


class OverlayType(Enum):
    STANDARD = "STANDARD",
    SETTLEMENT = "SETTLEMENT",
    CONSTRUCTION = "CONSTRUCTION",
    BLESSING = "BLESSING",
    DEPLOYMENT = "DEPLOYMENT",
    UNIT = "UNIT"


class Overlay:
    def __init__(self):
        self.showing: typing.List[OverlayType] = []
        self.current_turn: int = 0
        self.current_settlement: typing.Optional[Settlement] = None
        self.current_player: typing.Optional[Player] = None
        self.available_constructions: typing.List[typing.Union[Improvement, Unit]] = []
        self.selected_construction: typing.Optional[typing.Union[Improvement, Unit]] = None
        self.construction_boundaries: typing.Tuple[int, int] = 0, 5
        self.selected_unit: typing.Optional[Unit] = None
        self.available_blessings: typing.List[Blessing] = []
        self.selected_blessing: typing.Optional[Blessing] = None
        self.blessing_boundaries: typing.Tuple[int, int] = 0, 5
        
    def display(self):
        pyxel.load("resources/sprites.pyxres")
        if OverlayType.DEPLOYMENT in self.showing:
            pyxel.rectb(12, 150, 176, 15, pyxel.COLOR_WHITE)
            pyxel.rect(13, 151, 174, 13, pyxel.COLOR_BLACK)
            pyxel.text(15, 153, "Click a quad in the white square to deploy!", pyxel.COLOR_WHITE)
        else:
            if OverlayType.SETTLEMENT in self.showing:
                pyxel.rectb(12, 10, 176, 16, pyxel.COLOR_WHITE)
                pyxel.rect(13, 11, 174, 14, pyxel.COLOR_BLACK)
                pyxel.text(20, 14, self.current_settlement.name, self.current_player.colour)
                pyxel.blt(90, 12, 0, 0, 28, 8, 8)
                pyxel.text(100, 14, str(self.current_settlement.strength), pyxel.COLOR_WHITE)
                satisfaction_u = 8 if self.current_settlement.satisfaction >= 50 else 16
                pyxel.blt(115, 12, 0, satisfaction_u, 28, 8, 8)
                pyxel.text(125, 14, str(self.current_settlement.satisfaction), pyxel.COLOR_WHITE)
                pyxel.text(160, 14, f"{round(sum(quad.wealth for quad in self.current_settlement.quads))}", pyxel.COLOR_YELLOW)
                pyxel.text(166, 14, f"{round(sum(quad.harvest for quad in self.current_settlement.quads))}", pyxel.COLOR_GREEN)
                pyxel.text(172, 14, f"{round(sum(quad.zeal for quad in self.current_settlement.quads))}", pyxel.COLOR_RED)
                pyxel.text(178, 14, f"{round(sum(quad.fortune for quad in self.current_settlement.quads))}", pyxel.COLOR_PURPLE)

                pyxel.rectb(12, 130, 176, 40, pyxel.COLOR_WHITE)
                pyxel.rect(13, 131, 174, 38, pyxel.COLOR_BLACK)
                pyxel.line(100, 130, 100, 168, pyxel.COLOR_WHITE)
                pyxel.text(20, 134, "Construction", pyxel.COLOR_RED)
                if self.current_settlement.current_work is not None:
                    current_work = self.current_settlement.current_work
                    remaining_work = current_work.construction.cost - current_work.zeal_consumed
                    remaining_turns = math.ceil(remaining_work /
                                                sum(quad.zeal for quad in self.current_settlement.quads) +
                                                sum(imp.effect.zeal for imp in self.current_settlement.improvements))
                    pyxel.text(20, 145, current_work.construction.name, pyxel.COLOR_WHITE)
                    pyxel.text(20, 155, f"{remaining_turns} turns remaining", pyxel.COLOR_WHITE)
                else:
                    pyxel.text(20, 145, "None", pyxel.COLOR_RED)
                    pyxel.text(20, 155, "Press C to add one!", pyxel.COLOR_WHITE)
                pyxel.text(110, 134, "Garrison", pyxel.COLOR_RED)
                if len(self.current_settlement.garrison) > 0:
                    pluralisation = "s" if len(self.current_settlement.garrison) > 1 else ""
                    pyxel.text(110, 145, f"{len(self.current_settlement.garrison)} unit{pluralisation}", pyxel.COLOR_WHITE)
                    pyxel.text(110, 155, "Press D to deploy!", pyxel.COLOR_WHITE)
                else:
                    pyxel.text(110, 145, "No units.", pyxel.COLOR_RED)
            if OverlayType.CONSTRUCTION in self.showing:
                pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
                pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
                pyxel.text(55, 25, "Available constructions", pyxel.COLOR_RED)
                total_zeal = 0
                for setl in self.current_player.settlements:
                    total_zeal += sum(quad.zeal for quad in setl.quads)
                    total_zeal += sum(imp.effect.zeal for imp in setl.improvements)
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
                pyxel.text(90, 150, "Cancel", pyxel.COLOR_RED if self.selected_construction is None else pyxel.COLOR_WHITE)
            if OverlayType.UNIT in self.showing:
                pyxel.rectb(12, 130, 56, 40, pyxel.COLOR_WHITE)
                pyxel.rect(13, 131, 54, 38, pyxel.COLOR_BLACK)
                pyxel.text(20, 134, self.selected_unit.name, pyxel.COLOR_WHITE)
                pyxel.blt(20, 140, 0, 8, 36, 8, 8)
                pyxel.text(30, 142, str(self.selected_unit.health), pyxel.COLOR_WHITE)
                pyxel.blt(20, 150, 0, 0, 36, 8, 8)
                pyxel.text(30, 152, str(self.selected_unit.power), pyxel.COLOR_WHITE)
                pyxel.blt(20, 160, 0, 16, 36, 8, 8)
                pyxel.text(30, 162, f"{self.selected_unit.remaining_stamina}/{self.selected_unit.total_stamina}", pyxel.COLOR_WHITE)
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
                        total_fortune += sum(quad.fortune for quad in setl.quads)
                        total_fortune += sum(imp.effect.fortune for imp in setl.improvements)
                    remaining_turns = math.ceil(remaining_work / total_fortune)
                    pyxel.text(30, 50, ong_blessing.blessing.name, pyxel.COLOR_WHITE)
                    pyxel.text(30, 60, f"{remaining_turns} turns remaining", pyxel.COLOR_WHITE)
                else:
                    pyxel.text(30, 50, "None", pyxel.COLOR_RED)
                    pyxel.text(30, 60, "Press F to add one!", pyxel.COLOR_WHITE)
                pyxel.text(30, 80, "Wealth", pyxel.COLOR_YELLOW)
                wealth_per_turn = 0
                for setl in self.current_player.settlements:
                    wealth_per_turn += sum(quad.wealth for quad in setl.quads)
                    wealth_per_turn += sum(imp.effect.wealth for imp in setl.improvements)
                pyxel.text(30, 90, f"{self.current_player.wealth} (+{round(wealth_per_turn, 2)})", pyxel.COLOR_WHITE)
            if OverlayType.BLESSING in self.showing:
                pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
                pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
                pyxel.text(65, 25, "Available blessings", pyxel.COLOR_PURPLE)
                total_fortune = 0
                for setl in self.current_player.settlements:
                    total_fortune += sum(quad.fortune for quad in setl.quads)
                    total_fortune += sum(imp.effect.fortune for imp in setl.improvements)
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
                        for type_idx, unl_type in enumerate(types_unlockable):
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
                pyxel.text(90, 150, "Cancel", pyxel.COLOR_RED if self.selected_blessing is None else pyxel.COLOR_WHITE)

    def toggle_standard(self, turn: int):
        if OverlayType.STANDARD in self.showing:
            self.showing.pop()
        else:
            self.showing.append(OverlayType.STANDARD)
            self.current_turn = turn

    def toggle_construction(self, available_constructions: typing.List[typing.Union[Improvement, Unit]]):
        if OverlayType.CONSTRUCTION in self.showing and OverlayType.STANDARD not in self.showing:
            self.showing.pop()
        elif OverlayType.STANDARD not in self.showing:
            self.showing.append(OverlayType.CONSTRUCTION)
            self.available_constructions = available_constructions
            self.selected_construction = self.available_constructions[0]

    def navigate_constructions(self, down: bool):
        if down and self.selected_construction is not None:
            current_index = self.available_constructions.index(self.selected_construction)
            if current_index != len(self.available_constructions) - 1:
                self.selected_construction = self.available_constructions[current_index + 1]
                if current_index == self.construction_boundaries[1]:
                    self.construction_boundaries = \
                        self.construction_boundaries[0] + 1, self.construction_boundaries[1] + 1
            else:
                self.selected_construction = None
        elif not down:
            if self.selected_construction is None:
                self.selected_construction = self.available_constructions[len(self.available_constructions) - 1]
            else:
                current_index = self.available_constructions.index(self.selected_construction)
                if current_index != 0:
                    self.selected_construction = self.available_constructions[current_index - 1]
                    if current_index == self.construction_boundaries[0]:
                        self.construction_boundaries = \
                            self.construction_boundaries[0] - 1, self.construction_boundaries[1] - 1

    def is_constructing(self) -> bool:
        return OverlayType.CONSTRUCTION in self.showing

    def toggle_blessing(self, available_blessings: typing.List[Blessing]):
        if OverlayType.BLESSING in self.showing:
            self.showing.pop()
        else:
            self.showing.append(OverlayType.BLESSING)
            self.available_blessings = available_blessings
            self.selected_blessing = self.available_blessings[0]

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
        if OverlayType.SETTLEMENT in self.showing and len(self.showing) == 1:
            self.showing = []
        elif len(self.showing) == 0:
            self.showing.append(OverlayType.SETTLEMENT)
            self.current_settlement = settlement
            self.current_player = player

    def toggle_deployment(self):
        if OverlayType.DEPLOYMENT in self.showing:
            self.showing.pop()
        else:
            self.showing.append(OverlayType.DEPLOYMENT)

    def toggle_unit(self, unit: typing.Optional[Unit]):
        if OverlayType.UNIT in self.showing:
            self.showing.pop()
        else:
            self.showing.append(OverlayType.UNIT)
            self.selected_unit = unit
