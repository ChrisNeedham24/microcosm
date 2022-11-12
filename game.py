import time

import pyxel

from game_management.game_controller import GameController
from game_management.game_input_handler import GameInputHandler
from game_management.game_state import GameState


class Game:
    """
    The main class for the game. Contains the majority of business logic, and none of the drawing.
    """

    def __init__(self):
        """
        Initialises the game.
        """
        pyxel.init(200, 200, title="Microcosm", quit_key=pyxel.KEY_NONE)

        self.game_controller = GameController()
        self.game_state = GameState()

        pyxel.run(self.on_update, self.draw)

    def on_update(self):
        """
        On every update, calculate the elapsed time, manage music, and respond to key presses.
        """
        time_elapsed = time.time() - self.game_controller.last_time
        self.game_controller.last_time = time.time()

        if self.game_state.board is not None:
            self.game_state.board.update(time_elapsed)

        if self.game_state.on_menu:
            self.game_controller.music_player.restart_menu_if_necessary()
        elif not self.game_controller.music_player.is_playing():
            self.game_controller.music_player.next_song()

        all_units = []
        for player in self.game_state.players:
            for unit in player.units:
                all_units.append(unit)

        self.on_input(all_units)

    def draw(self):
        """
        Draws the game to the screen.
        """
        if self.game_state.on_menu:
            self.game_controller.menu.draw()
        elif self.game_state.game_started:
            self.game_state.board.draw(self.game_state.players, self.game_state.map_pos, self.game_state.turn,
                                       self.game_state.heathens, self.game_state.nighttime_left > 0,
                                       self.game_state.until_night if self.game_state.until_night != 0 else self.game_state.nighttime_left)

    def on_input(self, all_units):
        if pyxel.btnp(pyxel.KEY_DOWN):
            GameInputHandler().on_key_down(self.game_controller, self.game_state, pyxel.btn(pyxel.KEY_CTRL))
        elif pyxel.btnp(pyxel.KEY_UP):
            GameInputHandler().on_key_up(self.game_controller, self.game_state, pyxel.btn(pyxel.KEY_CTRL))
        elif pyxel.btnp(pyxel.KEY_LEFT):
            GameInputHandler().on_key_left(self.game_controller, self.game_state, pyxel.btn(pyxel.KEY_CTRL))
        elif pyxel.btnp(pyxel.KEY_RIGHT):
            GameInputHandler().on_key_right(self.game_controller, self.game_state, pyxel.btn(pyxel.KEY_CTRL))
        elif pyxel.btnp(pyxel.KEY_RETURN):
            GameInputHandler().on_key_return(self.game_controller, self.game_state)
        # Mouse clicks are forwarded to the Board for processing.
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            GameInputHandler().on_mouse_button_right(self.game_state)
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            GameInputHandler().on_mouse_button_left(self.game_state, all_units)
        elif pyxel.btnp(pyxel.KEY_SHIFT):
            GameInputHandler().on_key_shift(self.game_state)
        elif pyxel.btnp(pyxel.KEY_C):
            GameInputHandler().on_key_c(self.game_state)
        elif pyxel.btnp(pyxel.KEY_F):
            GameInputHandler().on_key_f(self.game_controller, self.game_state)
        elif pyxel.btnp(pyxel.KEY_D):
            GameInputHandler().on_key_d(self.game_state)
        elif pyxel.btnp(pyxel.KEY_TAB):
            GameInputHandler().on_key_tab(self.game_state)
        elif pyxel.btnp(pyxel.KEY_SPACE):
            GameInputHandler().on_key_space(self.game_controller, self.game_state)
        elif pyxel.btnp(pyxel.KEY_M):
            GameInputHandler().on_key_m(self.game_state)
        elif pyxel.btnp(pyxel.KEY_S):
            GameInputHandler().on_key_s(self.game_state)
        elif pyxel.btnp(pyxel.KEY_N):
            GameInputHandler().on_key_n(self.game_controller, self.game_state)
        elif pyxel.btnp(pyxel.KEY_B):
            GameInputHandler().on_key_b(self.game_state)
        elif pyxel.btnp(pyxel.KEY_ESCAPE):
            GameInputHandler().on_key_escape(self.game_state)
        elif pyxel.btnp(pyxel.KEY_A):
            GameInputHandler().on_key_a(self.game_state)
