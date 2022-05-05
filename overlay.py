import math
import typing
from enum import Enum

import pyxel

from models import Settlement, Player, Improvement, Unit


class OverlayType(Enum):
    STANDARD = "STANDARD",
    SETTLEMENT = "SETTLEMENT",
    CONSTRUCTION = "CONSTRUCTION",
    DEPLOYMENT = "DEPLOYMENT"


# TODO Add option for selected units

class Overlay:
    def __init__(self):
        self.showing: typing.List[OverlayType] = []
        self.current_turn: int = 0
        self.current_settlement: typing.Optional[Settlement] = None
        self.current_player: typing.Optional[Player] = None
        self.available_constructions: typing.List[typing.Union[Improvement, Unit]] = []
        self.selected_construction: typing.Optional[typing.Union[Improvement, Unit]] = None
        
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
                    remaining_turns = math.ceil(remaining_work / sum(quad.zeal for quad in self.current_settlement.quads))
                    pyxel.text(20, 145, self.current_settlement.current_work.construction.name, pyxel.COLOR_WHITE)
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
                for idx, construction in enumerate(self.available_constructions):
                    pyxel.text(30, 35 + idx * 18, construction.name, pyxel.COLOR_WHITE)
                    pyxel.text(150, 35 + idx * 18, "Build",
                               pyxel.COLOR_RED if self.selected_construction is construction else pyxel.COLOR_WHITE)
                    effects = 0
                    if construction.effect.wealth != 0:
                        sign = "+" if construction.effect.wealth > 0 else "-"
                        pyxel.text(30 + effects * 25, 42 + idx * 18,
                                   f"{sign}{abs(construction.effect.wealth)}", pyxel.COLOR_YELLOW)
                        effects += 1
                    if construction.effect.harvest != 0:
                        sign = "+" if construction.effect.harvest > 0 else "-"
                        pyxel.text(30 + effects * 25, 42 + idx * 18,
                                   f"{sign}{abs(construction.effect.harvest)}", pyxel.COLOR_GREEN)
                        effects += 1
                    if construction.effect.zeal != 0:
                        sign = "+" if construction.effect.zeal > 0 else "-"
                        pyxel.text(30 + effects * 25, 42 + idx * 18,
                                   f"{sign}{abs(construction.effect.zeal)}", pyxel.COLOR_RED)
                        effects += 1
                    if construction.effect.fortune != 0:
                        sign = "+" if construction.effect.fortune > 0 else "-"
                        pyxel.text(30 + effects * 25, 42 + idx * 18,
                                   f"{sign}{abs(construction.effect.fortune)}", pyxel.COLOR_PURPLE)
                        effects += 1
                    if construction.effect.strength != 0:
                        sign = "+" if construction.effect.strength > 0 else "-"
                        pyxel.blt(30 + effects * 25, 42 + idx * 18, 0, 0, 28, 8, 8)
                        pyxel.text(40 + effects * 25, 42 + idx * 18,
                                   f"{sign}{abs(construction.effect.strength)}", pyxel.COLOR_WHITE)
                        effects += 1
                    if construction.effect.satisfaction != 0:
                        sign = "+" if construction.effect.satisfaction > 0 else "-"
                        satisfaction_u = 8 if construction.effect.satisfaction >= 0 else 16
                        pyxel.blt(30 + effects * 25, 42 + idx * 18, 0, satisfaction_u, 28, 8, 8)
                        pyxel.text(40 + effects * 25, 42 + idx * 18,
                                   f"{sign}{abs(construction.effect.satisfaction)}", pyxel.COLOR_WHITE)
                pyxel.text(90, 150, "Cancel", pyxel.COLOR_RED if self.selected_construction is None else pyxel.COLOR_WHITE)
            if OverlayType.STANDARD in self.showing:
                pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
                pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
                pyxel.text(30, 30, "Turn", pyxel.COLOR_WHITE)
                pyxel.text(150, 30, str(self.current_turn), pyxel.COLOR_GREEN)

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
            else:
                self.selected_construction = None
        elif not down:
            if self.selected_construction is None:
                self.selected_construction = self.available_constructions[len(self.available_constructions) - 1]
            else:
                current_index = self.available_constructions.index(self.selected_construction)
                if current_index != 0:
                    self.selected_construction = self.available_constructions[current_index - 1]

    def is_constructing(self) -> bool:
        return OverlayType.CONSTRUCTION in self.showing

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
