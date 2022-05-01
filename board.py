import random
import typing
from enum import Enum

import pyxel

from calculator import calculate_yield_for_quad
from models import Player, Quad, Biome


class HelpOption(Enum):
    SETTLEMENT = "TAB: Next settlement"
    UNIT = "SPACE: Next unit"
    END_TURN = "ENTER: End turn"


class Board:
    def __init__(self):
        self.current_help = HelpOption.SETTLEMENT
        self.time_bank = 0

        self.quads: typing.List[Quad] = []
        self.generate_quads()

    def draw(self, players: typing.List[Player], map_pos: (int, int)):
        pyxel.cls(0)
        pyxel.rectb(0, 0, 100, 92, pyxel.COLOR_WHITE)
        pyxel.text(1, 93, self.current_help.value, pyxel.COLOR_WHITE)

        pyxel.load("resources/quads.pyxres")
        for idx, quad in enumerate(self.quads):
            col: int = idx % 100
            row = int(idx / 1000)
            if 0 <= col - map_pos[0] < 24 and 0 <= row - map_pos[1] < 22:
                quad_x: int = 0
                if quad.biome is Biome.FOREST:
                    quad_x = 4
                elif quad.biome is Biome.SEA:
                    quad_x = 8
                elif quad.biome is Biome.MOUNTAIN:
                    quad_x = 12
                pyxel.blt((col - map_pos[0]) * 4 + 2, (row - map_pos[1]) * 4 + 2, 0, quad_x, 0, 4, 4)

        pyxel.load("resources/sprites.pyxres")
        # for player in players:
        #     for settlement in player.settlements:
        #         pyxel.blt(settlement.location[0], settlement.location[1], 0, 0, 0, 15, 15)
        #     for unit in player.units:
        #         pyxel.blt(unit.location[0], unit.location[1], 1, 0, 0, 15, 30)

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

    def generate_quads(self):
        for _ in range(90000):
            biome = random.choice(list(Biome))
            quad_yield: (float, float, float, float) = calculate_yield_for_quad(biome)
            self.quads.append(Quad(biome, *quad_yield))
