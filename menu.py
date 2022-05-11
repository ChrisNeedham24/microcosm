import random
from enum import Enum

import pyxel


class MenuOption(Enum):
    NEW_GAME = "New Game"
    LOAD_GAME = "Load Game"
    EXIT = "Exit"


class Menu:
    def __init__(self):
        self.menu_option = MenuOption.NEW_GAME
        random.seed()
        self.image = random.randint(0, 3)

    def draw(self):
        if self.image < 3:
            pyxel.load("resources/background.pyxres")
            pyxel.blt(0, 0, self.image, 0, 0, 200, 200)
        else:
            pyxel.load("resources/background2.pyxres")
            pyxel.blt(0, 0, 0, 0, 0, 200, 200)
        pyxel.rectb(75, 120, 50, 60, pyxel.COLOR_WHITE)
        pyxel.rect(76, 121, 48, 58, pyxel.COLOR_BLACK)
        pyxel.text(82, 125, "MICROCOSM", pyxel.COLOR_WHITE)
        pyxel.text(85, 140, "New Game",
                   pyxel.COLOR_RED if self.menu_option is MenuOption.NEW_GAME else pyxel.COLOR_WHITE)
        pyxel.text(82, 155, "Load Game",
                   pyxel.COLOR_RED if self.menu_option is MenuOption.LOAD_GAME else pyxel.COLOR_WHITE)
        pyxel.text(92, 170, "Exit",
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
