import random
import typing
from enum import Enum

import pyxel

from calculator import calculate_yield_for_quad
from catalogue import get_default_unit
from models import Player, Quad, Biome, Settlement, Unit
from overlay import Overlay


class HelpOption(Enum):
    SETTLEMENT = "TAB: Next settlement"
    UNIT = "SPACE: Next unit"
    OVERLAY = "SHIFT: Show status overlay"
    END_TURN = "ENTER: End turn"


# TODO F Make it so biomes naturally cluster
# TODO F Show number of units with unspent movement
# TODO F Look into drawing issues with units/settlements on edge of map


class Board:
    def __init__(self):
        self.current_help = HelpOption.SETTLEMENT
        self.time_bank = 0

        self.quads: typing.List[typing.List[typing.Optional[Quad]]] = [[None] * 100 for _ in range(90)]
        self.generate_quads()

        self.quad_selected: typing.Optional[Quad] = None

        self.overlay = Overlay()
        self.selected_settlement: typing.Optional[Settlement] = None
        self.deploying_army = False
        self.selected_unit: typing.Optional[Unit] = None

    def draw(self, players: typing.List[Player], map_pos: (int, int), turn: int):
        pyxel.cls(0)
        pyxel.rectb(0, 0, 200, 184, pyxel.COLOR_WHITE)
        pyxel.text(2, 189, self.current_help.value, pyxel.COLOR_WHITE)
        pyxel.text(165, 189, f"Turn {turn}", pyxel.COLOR_WHITE)

        pyxel.load("resources/quads.pyxres")
        selected_quad_coords: (int, int) = None
        for i in range(map_pos[0], map_pos[0] + 24):
            for j in range(map_pos[1], map_pos[1] + 22):
                if 0 <= i <= 99 and 0 <= j <= 89:
                    quad = self.quads[j][i]
                    setl_x: int = 0
                    if quad.biome is Biome.FOREST:
                        setl_x = 8
                    elif quad.biome is Biome.SEA:
                        setl_x = 16
                    elif quad.biome is Biome.MOUNTAIN:
                        setl_x = 24
                    pyxel.blt((i - map_pos[0]) * 8 + 4, (j - map_pos[1]) * 8 + 4, 0, setl_x, 4, 8, 8)
                    if quad.selected:
                        selected_quad_coords = i, j
                        pyxel.rectb((i - map_pos[0]) * 8 + 4, (j - map_pos[1]) * 8 + 4, 8, 8, pyxel.COLOR_RED)

        pyxel.load("resources/sprites.pyxres")
        for player in players:
            for unit in player.units:
                quad: Quad = self.quads[unit.location[1]][unit.location[0]]
                unit_x: int = 0
                if quad.biome is Biome.FOREST:
                    unit_x = 8
                elif quad.biome is Biome.SEA:
                    unit_x = 16
                elif quad.biome is Biome.MOUNTAIN:
                    unit_x = 24
                pyxel.blt((unit.location[0] - map_pos[0]) * 8 + 4,
                          (unit.location[1] - map_pos[1]) * 8 + 4, 0, unit_x, 16, 8, 8)
                if self.selected_unit is unit:
                    pyxel.rectb((unit.location[0] - map_pos[0]) * 8 + 4,
                                (unit.location[1] - map_pos[1]) * 8 + 4, 8, 8, pyxel.COLOR_RED)
                    movement = self.selected_unit.remaining_stamina
                    pyxel.rectb((self.selected_unit.location[0] - map_pos[0]) * 8 + 4 - (movement * 8),
                                (self.selected_unit.location[1] - map_pos[1]) * 8 + 4 - (movement * 8),
                                (2 * movement + 1) * 8, (2 * movement + 1) * 8, pyxel.COLOR_WHITE)
            for settlement in player.settlements:
                quad: Quad = self.quads[settlement.location[1]][settlement.location[0]]
                setl_x: int = 0
                if quad.biome is Biome.FOREST:
                    setl_x = 8
                elif quad.biome is Biome.SEA:
                    setl_x = 16
                elif quad.biome is Biome.MOUNTAIN:
                    setl_x = 24
                base_x_pos = (settlement.location[0] - map_pos[0]) * 8
                base_y_pos = (settlement.location[1] - map_pos[1]) * 8
                pyxel.blt(base_x_pos + 4, base_y_pos + 4, 0, setl_x, 4, 8, 8)
                if self.selected_settlement is not settlement:
                    pyxel.rectb(base_x_pos - 17, base_y_pos - 8, 52, 10, pyxel.COLOR_BLACK)
                    pyxel.rect(base_x_pos - 16, base_y_pos - 7, 50, 8, player.colour)
                    pyxel.text(base_x_pos - 10, base_y_pos - 6, settlement.name, pyxel.COLOR_WHITE)
                else:
                    pyxel.rectb((settlement.location[0] - map_pos[0]) * 8 + 4,
                                (settlement.location[1] - map_pos[1]) * 8 + 4, 8, 8, pyxel.COLOR_RED)

        if self.quad_selected is not None and selected_quad_coords is not None:
            x_offset = 30 if selected_quad_coords[0] - map_pos[0] <= 8 else 0
            y_offset = -34 if selected_quad_coords[1] - map_pos[1] >= 36 else 0
            base_x_pos = (selected_quad_coords[0] - map_pos[0]) * 8 + x_offset
            base_y_pos = (selected_quad_coords[1] - map_pos[1]) * 8 + y_offset
            pyxel.rectb(base_x_pos - 22, base_y_pos + 8, 30, 12, pyxel.COLOR_WHITE)
            pyxel.rect(base_x_pos - 21, base_y_pos + 9, 28, 10, pyxel.COLOR_BLACK)
            pyxel.text(base_x_pos - 18, base_y_pos + 12, f"{round(self.quad_selected.wealth)}", pyxel.COLOR_YELLOW)
            pyxel.text(base_x_pos - 12, base_y_pos + 12, f"{round(self.quad_selected.harvest)}", pyxel.COLOR_GREEN)
            pyxel.text(base_x_pos - 6, base_y_pos + 12, f"{round(self.quad_selected.zeal)}", pyxel.COLOR_RED)
            pyxel.text(base_x_pos, base_y_pos + 12, f"{round(self.quad_selected.fortune)}", pyxel.COLOR_PURPLE)

        if self.deploying_army:
            pyxel.rectb((self.selected_settlement.location[0] - map_pos[0]) * 8 - 4,
                        (self.selected_settlement.location[1] - map_pos[1]) * 8 - 4, 24, 24, pyxel.COLOR_WHITE)

        self.overlay.display()

    def update(self, elapsed_time: float):
        self.time_bank += elapsed_time
        if self.time_bank > 3:
            if self.current_help is HelpOption.SETTLEMENT:
                self.current_help = HelpOption.UNIT
            elif self.current_help is HelpOption.UNIT:
                self.current_help = HelpOption.OVERLAY
            elif self.current_help is HelpOption.OVERLAY:
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
        if 4 <= mouse_x <= 196 and 4 <= mouse_y <= 180:
            adj_x = int((mouse_x - 4) / 8) + map_pos[0]
            adj_y = int((mouse_y - 4) / 8) + map_pos[1]
            self.quads[adj_y][adj_x].selected = True if not self.quads[adj_y][adj_x].selected else False
            if self.quad_selected is not None:
                self.quad_selected.selected = False
            self.quad_selected = self.quads[adj_y][adj_x]

    def process_left_click(self, mouse_x: int, mouse_y: int, settled: bool,
                           player: Player, map_pos: (int, int)):
        if 4 <= mouse_x <= 196 and 4 <= mouse_y <= 180:
            adj_x = int((mouse_x - 4) / 8) + map_pos[0]
            adj_y = int((mouse_y - 4) / 8) + map_pos[1]
            if not settled:
                new_settl = Settlement("Protevousa", [], 100, 50, (adj_x, adj_y), [self.quads[adj_y][adj_x]],
                                       [get_default_unit((adj_x, adj_y))], None)
                player.settlements.append(new_settl)
                self.overlay.toggle_tutorial()
                self.selected_settlement = new_settl
                self.overlay.toggle_settlement(new_settl, player)
            else:
                if not self.deploying_army and \
                        self.selected_settlement is not None and self.selected_settlement.location != (adj_x, adj_y):
                    self.selected_settlement = None
                    self.overlay.toggle_settlement(None, player)
                elif self.selected_unit is None and self.selected_settlement is None and \
                        any((to_select := setl).location == (adj_x, adj_y) for setl in player.settlements):
                    self.selected_settlement = to_select
                    self.overlay.toggle_settlement(to_select, player)
                elif self.deploying_army and \
                        self.selected_settlement.location[0] - 1 <= adj_x <= self.selected_settlement.location[0] + 1 and \
                        self.selected_settlement.location[1] - 1 <= adj_y <= self.selected_settlement.location[1] + 1:
                    deployed = self.selected_settlement.garrison.pop()
                    deployed.garrisoned = False
                    deployed.location = adj_x, adj_y
                    player.units.append(deployed)
                    self.deploying_army = False
                    self.selected_unit = deployed
                    self.overlay.toggle_deployment()
                    self.selected_settlement = None
                    self.overlay.toggle_settlement(None, player)
                    self.overlay.toggle_unit(deployed)
                elif self.selected_unit is not None and \
                        self.selected_unit.location[0] - self.selected_unit.remaining_stamina <= adj_x <= \
                        self.selected_unit.location[0] + self.selected_unit.remaining_stamina and \
                        self.selected_unit.location[1] - self.selected_unit.remaining_stamina <= adj_y <= \
                        self.selected_unit.location[1] + self.selected_unit.remaining_stamina:
                    initial = self.selected_unit.location
                    distance_travelled = max(abs(initial[0] - adj_x), abs(initial[1] - adj_y))
                    self.selected_unit.remaining_stamina -= distance_travelled
                    self.selected_unit.location = adj_x, adj_y
                elif self.selected_unit is not None and self.selected_unit.location != (adj_x, adj_y):
                    self.selected_unit = None
                    self.overlay.toggle_unit(None)
                elif self.selected_unit is None and \
                        any((to_select := unit).location == (adj_x, adj_y) for unit in player.units):
                    self.selected_unit = to_select
                    self.overlay.toggle_unit(to_select)
