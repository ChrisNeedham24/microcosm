import random
import typing
from enum import Enum

import pyxel

from calculator import clamp
from models import GameConfig


class MenuOption(Enum):
    NEW_GAME = "New Game"
    LOAD_GAME = "Load Game"
    EXIT = "Exit"


class SetupOption(Enum):
    PLAYER_COLOUR = "COLOUR",
    PLAYER_COUNT = "COUNT",
    BIOME_CLUSTERING = "BIOME",
    FOG_OF_WAR = "FOG",
    START_GAME = "START"


AVAILABLE_COLOURS = [
    ("Navy", pyxel.COLOR_NAVY),
    ("Purple", pyxel.COLOR_PURPLE),
    ("Green", pyxel.COLOR_GREEN),
    ("Brown", pyxel.COLOR_BROWN),
    ("Dark blue", pyxel.COLOR_DARK_BLUE),
    ("Light blue", pyxel.COLOR_LIGHT_BLUE),
    ("Red", pyxel.COLOR_RED),
    ("Orange", pyxel.COLOR_ORANGE),
    ("Yellow", pyxel.COLOR_YELLOW),
    ("Lime", pyxel.COLOR_LIME),
    ("Cyan", pyxel.COLOR_CYAN),
    ("Grey", pyxel.COLOR_GRAY),
    ("Pink", pyxel.COLOR_PINK),
    ("Peach", pyxel.COLOR_PEACH)
]


class Menu:
    def __init__(self):
        self.menu_option = MenuOption.NEW_GAME
        random.seed()
        self.image = random.randint(0, 3)
        self.in_game_setup = False
        self.loading_game = False
        self.saves: typing.List[str] = []
        self.save_idx: typing.Optional[int] = 0
        self.setup_option = SetupOption.PLAYER_COLOUR
        self.colour_idx = 0
        self.player_count = 2
        self.biome_clustering_enabled = True
        self.fog_of_war_enabled = True

    def draw(self):
        if self.image < 3:
            pyxel.load("resources/background.pyxres")
            pyxel.blt(0, 0, self.image, 0, 0, 200, 200)
        else:
            pyxel.load("resources/background2.pyxres")
            pyxel.blt(0, 0, 0, 0, 0, 200, 200)
        if self.in_game_setup:
            pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
            pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
            pyxel.text(81, 25, "Game Setup", pyxel.COLOR_WHITE)
            pyxel.text(28, 40, "Player Colour",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.PLAYER_COLOUR else pyxel.COLOR_WHITE)
            colour_offset = 5 - len(AVAILABLE_COLOURS[self.colour_idx][0])
            if self.colour_idx == 0:
                pyxel.text(130 + colour_offset, 40, f"{AVAILABLE_COLOURS[self.colour_idx][0]} ->",
                           AVAILABLE_COLOURS[self.colour_idx][1])
            elif self.colour_idx == len(AVAILABLE_COLOURS) - 1:
                pyxel.text(130 + colour_offset, 40, f"<- {AVAILABLE_COLOURS[self.colour_idx][0]}",
                           AVAILABLE_COLOURS[self.colour_idx][1])
            else:
                pyxel.text(120 + colour_offset, 40, f"<- {AVAILABLE_COLOURS[self.colour_idx][0]} ->",
                           AVAILABLE_COLOURS[self.colour_idx][1])
            pyxel.text(28, 60, "Player Count",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.PLAYER_COUNT else pyxel.COLOR_WHITE)
            if self.player_count == 2:
                pyxel.text(140, 60, "2 ->", pyxel.COLOR_WHITE)
            elif 2 < self.player_count < 14:
                pyxel.text(130, 60, f"<- {self.player_count} ->", pyxel.COLOR_WHITE)
            else:
                pyxel.text(130, 60, "<- 14", pyxel.COLOR_WHITE)
            pyxel.text(28, 80, "Biome Clustering",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.BIOME_CLUSTERING else pyxel.COLOR_WHITE)
            if self.biome_clustering_enabled:
                pyxel.text(125, 80, "<- Enabled", pyxel.COLOR_GREEN)
            else:
                pyxel.text(125, 80, "Disabled ->", pyxel.COLOR_RED)
            pyxel.text(28, 100, "Fog of War",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.FOG_OF_WAR else pyxel.COLOR_WHITE)
            if self.fog_of_war_enabled:
                pyxel.text(125, 100, "<- Enabled", pyxel.COLOR_GREEN)
            else:
                pyxel.text(125, 100, "Disabled ->", pyxel.COLOR_RED)
            pyxel.text(81, 150, "Start Game",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.START_GAME else pyxel.COLOR_WHITE)
        elif self.loading_game:
            pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
            pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
            pyxel.text(81, 25, "Load Game", pyxel.COLOR_WHITE)
            for idx, save in enumerate(self.saves):
                pyxel.text(25, 35 + idx * 10, save, pyxel.COLOR_WHITE)
                pyxel.text(150, 35 + idx * 10, "Load", pyxel.COLOR_RED if self.save_idx is idx else pyxel.COLOR_WHITE)
            pyxel.text(85, 150, "Cancel", pyxel.COLOR_RED if self.save_idx == -1 else pyxel.COLOR_WHITE)
        else:
            pyxel.rectb(75, 120, 50, 60, pyxel.COLOR_WHITE)
            pyxel.rect(76, 121, 48, 58, pyxel.COLOR_BLACK)
            pyxel.text(82, 125, "MICROCOSM", pyxel.COLOR_WHITE)
            pyxel.text(85, 140, "New Game",
                       pyxel.COLOR_RED if self.menu_option is MenuOption.NEW_GAME else pyxel.COLOR_WHITE)
            pyxel.text(82, 155, "Load Game",
                       pyxel.COLOR_RED if self.menu_option is MenuOption.LOAD_GAME else pyxel.COLOR_WHITE)
            pyxel.text(92, 170, "Exit",
                       pyxel.COLOR_RED if self.menu_option is MenuOption.EXIT else pyxel.COLOR_WHITE)

    def navigate(self, up: bool = False, down: bool = False, left: bool = False, right: bool = False):
        if down:
            if self.in_game_setup:
                if self.setup_option is SetupOption.PLAYER_COLOUR:
                    self.setup_option = SetupOption.PLAYER_COUNT
                elif self.setup_option is SetupOption.PLAYER_COUNT:
                    self.setup_option = SetupOption.BIOME_CLUSTERING
                elif self.setup_option is SetupOption.BIOME_CLUSTERING:
                    self.setup_option = SetupOption.FOG_OF_WAR
                elif self.setup_option is SetupOption.FOG_OF_WAR:
                    self.setup_option = SetupOption.START_GAME
            elif self.loading_game:
                if 0 <= self.save_idx < len(self.saves) - 1:
                    self.save_idx += 1
                elif self.save_idx == len(self.saves) - 1:
                    self.save_idx = -1
            else:
                if self.menu_option is MenuOption.NEW_GAME:
                    self.menu_option = MenuOption.LOAD_GAME
                elif self.menu_option is MenuOption.LOAD_GAME:
                    self.menu_option = MenuOption.EXIT
        if up:
            if self.in_game_setup:
                if self.setup_option is SetupOption.PLAYER_COUNT:
                    self.setup_option = SetupOption.PLAYER_COLOUR
                elif self.setup_option is SetupOption.BIOME_CLUSTERING:
                    self.setup_option = SetupOption.PLAYER_COUNT
                elif self.setup_option is SetupOption.FOG_OF_WAR:
                    self.setup_option = SetupOption.BIOME_CLUSTERING
                elif self.setup_option is SetupOption.START_GAME:
                    self.setup_option = SetupOption.FOG_OF_WAR
            elif self.loading_game:
                if self.save_idx == -1:
                    self.save_idx = len(self.saves) - 1
                elif self.save_idx > 0:
                    self.save_idx -= 1
            else:
                if self.menu_option is MenuOption.LOAD_GAME:
                    self.menu_option = MenuOption.NEW_GAME
                elif self.menu_option is MenuOption.EXIT:
                    self.menu_option = MenuOption.LOAD_GAME
        if left:
            if self.setup_option is SetupOption.PLAYER_COLOUR:
                self.colour_idx = clamp(self.colour_idx - 1, 0, len(AVAILABLE_COLOURS) - 1)
            elif self.setup_option is SetupOption.PLAYER_COUNT:
                self.player_count = max(2, self.player_count - 1)
            elif self.setup_option is SetupOption.BIOME_CLUSTERING:
                self.biome_clustering_enabled = False
            elif self.setup_option is SetupOption.FOG_OF_WAR:
                self.fog_of_war_enabled = False
        if right:
            if self.setup_option is SetupOption.PLAYER_COLOUR:
                self.colour_idx = clamp(self.colour_idx + 1, 0, len(AVAILABLE_COLOURS) - 1)
            elif self.setup_option is SetupOption.PLAYER_COUNT:
                self.player_count = min(14, self.player_count + 1)
            elif self.setup_option is SetupOption.BIOME_CLUSTERING:
                self.biome_clustering_enabled = True
            elif self.setup_option is SetupOption.FOG_OF_WAR:
                self.fog_of_war_enabled = True

    def get_game_config(self) -> GameConfig:
        return GameConfig(self.player_count, AVAILABLE_COLOURS[self.colour_idx][1], self.biome_clustering_enabled,
                          self.fog_of_war_enabled)
