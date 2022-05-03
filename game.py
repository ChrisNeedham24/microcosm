import time
import typing

import pyxel

from board import Board
from calculator import clamp
from menu import Menu, MenuOption
from models import Player, Settlement


class Game:
    def __init__(self):
        pyxel.init(100, 100, title="Microcosm")

        self.menu = Menu()
        self.board = Board()
        self.players: typing.List[Player] = [Player("Test", pyxel.COLOR_RED, [], [], [])]

        self.on_menu = True
        self.game_started = False

        self.last_time = time.time()

        self.map_pos: (int, int) = 0, 0
        self.turn = 1

        # pyxel.play(0, 0, loop=True)

        pyxel.run(self.on_update, self.draw)

    def on_update(self):
        time_elapsed = time.time() - self.last_time
        self.last_time = time.time()

        self.board.update(time_elapsed)

        if pyxel.btnp(pyxel.KEY_DOWN):
            if self.on_menu:
                self.menu.navigate(True)
            elif self.game_started:
                self.map_pos = self.map_pos[0], clamp(self.map_pos[1] + 1, -1, 69)
        elif pyxel.btnp(pyxel.KEY_UP):
            if self.on_menu:
                self.menu.navigate(False)
            elif self.game_started:
                self.map_pos = self.map_pos[0], clamp(self.map_pos[1] - 1, -1, 69)
        elif pyxel.btnp(pyxel.KEY_LEFT):
            if self.game_started:
                self.map_pos = clamp(self.map_pos[0] - 1, -1, 77), self.map_pos[1]
        elif pyxel.btnp(pyxel.KEY_RIGHT):
            if self.game_started:
                self.map_pos = clamp(self.map_pos[0] + 1, -1, 77), self.map_pos[1]
        elif pyxel.btnp(pyxel.KEY_RETURN):
            if self.on_menu:
                if self.menu.menu_option is MenuOption.NEW_GAME:
                    pyxel.mouse(visible=True)
                    self.game_started = True
                    self.on_menu = False
                elif self.menu.menu_option is MenuOption.LOAD_GAME:
                    print("Unsupported for now.")
                elif self.menu.menu_option is MenuOption.EXIT:
                    pyxel.quit()
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            if self.game_started:
                self.board.process_right_click(pyxel.mouse_x, pyxel.mouse_y, self.map_pos)
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if self.game_started:
                self.board.process_left_click(pyxel.mouse_x, pyxel.mouse_y,
                                              len(self.players[0].settlements) > 0,
                                              self.players[0], self.map_pos)
        elif pyxel.btnp(pyxel.KEY_SHIFT):
            if self.game_started:
                self.board.showing_overlay = not self.board.showing_overlay

    def draw(self):
        if self.on_menu:
            self.menu.draw()
        elif self.game_started:
            self.board.draw(self.players, self.map_pos, self.turn)
