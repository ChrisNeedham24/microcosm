import random
import typing
from enum import Enum

import pyxel

from calculator import calculate_yield_for_quad
from models import Player, Quad, Biome, Settlement, Unit
from overlay import Overlay


class HelpOption(Enum):
    SETTLEMENT = "TAB: Next settlement"
    UNIT = "SPACE: Next unit"
    END_TURN = "ENTER: End turn"


class Board:
    def __init__(self):
        self.current_help = HelpOption.SETTLEMENT
        self.time_bank = 0

        self.quads: typing.List[typing.List[Quad or None]] = [[None] * 100 for _ in range(90)]
        self.generate_quads()

        self.quad_selected: Quad or None = None

        self.overlay = Overlay()
        self.showing_overlay = False
        self.selected_settlement: Settlement or None = None

    def draw(self, players: typing.List[Player], map_pos: (int, int), turn: int):
        pyxel.cls(0)
        pyxel.rectb(0, 0, 100, 92, pyxel.COLOR_WHITE)
        pyxel.text(1, 93, self.current_help.value, pyxel.COLOR_WHITE)

        pyxel.load("resources/quads.pyxres")
        selected_quad_coords: (int, int) = None
        for i in range(map_pos[0], map_pos[0] + 24):
            for j in range(map_pos[1], map_pos[1] + 22):
                if 0 <= i <= 99 and 0 <= j <= 89:
                    quad = self.quads[j][i]
                    setl_x: int = 0
                    if quad.biome is Biome.FOREST:
                        setl_x = 4
                    elif quad.biome is Biome.SEA:
                        setl_x = 8
                    elif quad.biome is Biome.MOUNTAIN:
                        setl_x = 12
                    pyxel.blt((i - map_pos[0]) * 4 + 2, (j - map_pos[1]) * 4 + 2, 0, setl_x, 0, 4, 4)
                    if quad.selected:
                        selected_quad_coords = i, j
                        pyxel.rectb((i - map_pos[0]) * 4 + 2, (j - map_pos[1]) * 4 + 2, 4, 4, pyxel.COLOR_RED)

        pyxel.load("resources/sprites.pyxres")
        for player in players:
            for settlement in player.settlements:
                quad: Quad = self.quads[settlement.location[1]][settlement.location[0]]
                setl_x: int = 0
                if quad.biome is Biome.FOREST:
                    setl_x = 4
                elif quad.biome is Biome.SEA:
                    setl_x = 8
                elif quad.biome is Biome.MOUNTAIN:
                    setl_x = 12
                base_x_pos = (settlement.location[0] - map_pos[0]) * 4
                base_y_pos = (settlement.location[1] - map_pos[1]) * 4
                pyxel.blt(base_x_pos + 2, base_y_pos + 2, 0, setl_x, 0, 4, 4)
                pyxel.rectb(base_x_pos - 5, base_y_pos - 9, 20, 10, pyxel.COLOR_BLACK)
                pyxel.rect(base_x_pos - 4, base_y_pos - 8, 18, 8, player.colour)
                pyxel.text(base_x_pos - 2, base_y_pos - 7, "Setl", pyxel.COLOR_WHITE)
            for unit in player.units:
                pyxel.blt(unit.location[0], unit.location[1], 1, 0, 0, 15, 30)

        if self.quad_selected is not None and selected_quad_coords is not None:
            x_offset = 15 if selected_quad_coords[0] - map_pos[0] <= 4 else 0
            y_offset = -17 if selected_quad_coords[1] - map_pos[1] >= 18 else 0
            base_x_pos = (selected_quad_coords[0] - map_pos[0]) * 4 + x_offset
            base_y_pos = (selected_quad_coords[1] - map_pos[1]) * 4 + y_offset
            pyxel.rectb(base_x_pos - 11, base_y_pos + 4, 15, 17, pyxel.COLOR_WHITE)
            pyxel.rect(base_x_pos - 10, base_y_pos + 5, 13, 15, pyxel.COLOR_BLACK)
            pyxel.text(base_x_pos - 8, base_y_pos + 7, f"{round(self.quad_selected.wealth)}", pyxel.COLOR_YELLOW)
            pyxel.text(base_x_pos - 2, base_y_pos + 7, f"{round(self.quad_selected.harvest)}", pyxel.COLOR_GREEN)
            pyxel.text(base_x_pos - 8, base_y_pos + 13, f"{round(self.quad_selected.zeal)}", pyxel.COLOR_RED)
            pyxel.text(base_x_pos - 2, base_y_pos + 13, f"{round(self.quad_selected.fortune)}", pyxel.COLOR_PURPLE)

        if self.showing_overlay:
            self.overlay.draw(turn)
        if self.selected_settlement is not None:
            self.overlay.draw_settlement(self.selected_settlement, player)

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
        for i in range(100):
            for j in range(90):
                biome = random.choice(list(Biome))
                quad_yield: (float, float, float, float) = calculate_yield_for_quad(biome)
                self.quads[j][i] = Quad(biome, *quad_yield)

    def process_right_click(self, mouse_x: int, mouse_y: int, map_pos: (int, int)):
        if 2 <= mouse_x <= 98 and 2 <= mouse_y <= 90:
            adj_x = int((mouse_x - 2) / 4) + map_pos[0]
            adj_y = int((mouse_y - 2) / 4) + map_pos[1]
            self.quads[adj_y][adj_x].selected = True if not self.quads[adj_y][adj_x].selected else False
            if self.quad_selected is not None:
                self.quad_selected.selected = False
            self.quad_selected = self.quads[adj_y][adj_x]

    def process_left_click(self, mouse_x: int, mouse_y: int, settled: bool, player: Player, map_pos: (int, int)):
        if 2 <= mouse_x <= 98 and 2 <= mouse_y <= 90:
            adj_x = int((mouse_x - 2) / 4) + map_pos[0]
            adj_y = int((mouse_y - 2) / 4) + map_pos[1]
            if not settled:
                new_settl = Settlement("Protevousa", [], 100, 50, (adj_x, adj_y), [self.quads[adj_y][adj_x]],
                                       [Unit(100, 100, 3, (adj_x, adj_y), True)])
                player.settlements.append(new_settl)
                self.selected_settlement = new_settl

