import typing
from enum import Enum

import pyxel

from models import Player


class HelpOption(Enum):
    SETTLEMENT = "TAB: Next settlement"
    UNIT = "SPACE: Next unit"
    END_TURN = "ENTER: End turn"


class Board:
    def __init__(self):
        self.current_help = HelpOption.SETTLEMENT
        self.time_bank = 0

    def draw(self, players: typing.List[Player]):
        pyxel.cls(0)
        pyxel.rectb(0, 0, 100, 90, pyxel.COLOR_WHITE)
        pyxel.text(1, 91, self.current_help.value, pyxel.COLOR_WHITE)
        for player in players:
            for settlement in player.settlements:
                pyxel.blt(settlement.location[0], settlement.location[1], 0, 0, 0, 15, 15)
            for unit in player.units:
                pyxel.blt(unit.location[0], unit.location[1], 1, 0, 0, 15, 30)

    def update(self, elapsed_time: float):
        self.time_bank += elapsed_time
        if self.time_bank > 3:
            if self.current_help is HelpOption.SETTLEMENT:
                self.current_help = HelpOption.UNIT
            elif self.current_help is HelpOption.UNIT:
                self.current_help = HelpOption.END_TURN
            elif self.current_help is HelpOption.END_TURN:
                self.current_help = HelpOption.SETTLEMENT
            self.time_bank = 0
