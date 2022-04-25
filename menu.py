from enum import Enum

import pyxel


class MenuOption(Enum):
    NEW_GAME = "New Game"
    LOAD_GAME = "Load Game"
    EXIT = "Exit"


class Menu:
    def __init__(self):
        pyxel.load("resources/title_text.pyxres")
        self.menu_option = MenuOption.NEW_GAME

    def draw(self):
        pyxel.cls(0)
        pyxel.image(0)
        pyxel.blt(20, 30, 0, 0, 0, 100, 100)
