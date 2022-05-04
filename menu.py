from enum import Enum

import pyxel


class MenuOption(Enum):
    NEW_GAME = "New Game"
    LOAD_GAME = "Load Game"
    EXIT = "Exit"


class Menu:
    def __init__(self):
        self.menu_option = MenuOption.NEW_GAME

    def draw(self):
        pyxel.cls(0)
        pyxel.text(82, 60, "MICROCOSM", pyxel.COLOR_WHITE)
        pyxel.text(85, 100, "New Game",
                   pyxel.COLOR_RED if self.menu_option is MenuOption.NEW_GAME else pyxel.COLOR_WHITE)
        pyxel.text(82, 120, "Load Game",
                   pyxel.COLOR_RED if self.menu_option is MenuOption.LOAD_GAME else pyxel.COLOR_WHITE)
        pyxel.text(92, 140, "Exit",
                   pyxel.COLOR_RED if self.menu_option is MenuOption.EXIT else pyxel.COLOR_WHITE)

    def navigate(self, down: bool):
        if down:
            if self.menu_option is MenuOption.NEW_GAME:
                self.menu_option = MenuOption.LOAD_GAME
            elif self.menu_option is MenuOption.LOAD_GAME:
                self.menu_option = MenuOption.EXIT
        else:
            if self.menu_option is MenuOption.LOAD_GAME:
                self.menu_option = MenuOption.NEW_GAME
            elif self.menu_option is MenuOption.EXIT:
                self.menu_option = MenuOption.LOAD_GAME
