import typing
from enum import Enum

import pyxel

from models import Settlement, Player, Improvement, Unit


class OverlayType(Enum):
    STANDARD = "STANDARD",
    SETTLEMENT = "SETTLEMENT",
    CONSTRUCTION = "CONSTRUCTION"


class Overlay:
    def __init__(self):
        self.showing: typing.List[OverlayType] = []
        self.current_turn: int = 0
        self.current_settlement: typing.Optional[Settlement] = None
        self.current_player: typing.Optional[Player] = None
        self.available_constructions: typing.List[typing.Union[Improvement, Unit]] = []
        self.selected_construction: typing.Optional[typing.Union[Improvement, Unit]] = None
        
    def display(self):
        if OverlayType.SETTLEMENT in self.showing:
            pyxel.load("resources/sprites.pyxres")
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
                pyxel.text(20, 145, self.current_settlement.current_work.construction.name, pyxel.COLOR_WHITE)
            else:
                pyxel.text(20, 145, "None", pyxel.COLOR_RED)
                pyxel.text(20, 155, "Press A to add one!", pyxel.COLOR_WHITE)
        if OverlayType.CONSTRUCTION in self.showing:
            pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
            pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
            pyxel.text(55, 25, "Available constructions", pyxel.COLOR_RED)
            for idx, construction in enumerate(self.available_constructions):
                pyxel.text(30, 35 + idx * 20, construction.name, pyxel.COLOR_WHITE)
                pyxel.text(150, 35 + idx * 20, "Build",
                           pyxel.COLOR_RED if self.selected_construction is construction else pyxel.COLOR_WHITE)
                # TODO Add effects underneath construction name.
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
