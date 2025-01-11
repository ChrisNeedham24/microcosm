import sys
import time
from threading import Thread

import pyxel
from PIL import Image

# In cases where we're running from a pip-installed distribution, monkey patch the source module, since it'll actually
# be under 'microcosm.source' in site-packages.
if "microcosm" in sys.modules:
    import microcosm.source as source
    sys.modules["source"] = source

from source.game_management.game_controller import GameController
from source.game_management.game_input_handler import on_key_arrow_down, on_key_arrow_up, on_key_arrow_left, \
    on_key_arrow_right, on_key_return, on_mouse_button_right, on_mouse_button_left, on_key_shift, on_key_c, on_key_f, \
    on_key_d, on_key_tab, on_key_space, on_key_m, on_key_s, on_key_n, on_key_b, on_key_escape, on_key_a, on_key_j, \
    on_key_x
from source.game_management.game_state import GameState
from source.networking.event_listener import EventListener
from source.saving.game_save_manager import init_app_data
from source.util.converter import convert_image_to_pyxel_icon_data


class Game:
    """
    The main class for the game. Contains the main game loop and subsequent state and controls, and none of the drawing.
    The state of the game is available in GameState - and game controlling mechanisms are available in GameController.
    """

    def __init__(self):
        """
        Initialises the game, including the directories required for save data.
        """
        init_app_data()

        pyxel.init(200, 200, title="Microcosm", display_scale=5, quit_key=pyxel.KEY_NONE)

        icon_image: Image = Image.open("resources/icon.png")
        pyxel.icon(convert_image_to_pyxel_icon_data(icon_image), 1)

        self.game_controller = GameController()
        self.game_state = GameState()

        # Start the multiplayer EventListener in another thread so that it doesn't block pyxel running. Since it is
        # passed references to the game state and controller, it is still able to modify them while pyxel is running.
        client_listener: EventListener = EventListener(game_states={"local": self.game_state},
                                                       game_controller=self.game_controller)
        listener_thread: Thread = Thread(target=client_listener.run)
        listener_thread.start()

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

        self.on_input()

    def draw(self):
        """
        Draws the game to the screen.
        """
        if self.game_state.on_menu:
            self.game_controller.menu.draw()
        elif self.game_state.game_started:
            self.game_state.board.draw(self.game_state.players, self.game_state.map_pos, self.game_state.turn,
                                       self.game_state.heathens, self.game_state.nighttime_left > 0,
                                       self.game_state.until_night if self.game_state.until_night != 0
                                       else self.game_state.nighttime_left)

    def on_input(self):
        """
        Handles an input event from the user in the game loop.
        """
        if pyxel.btnp(pyxel.KEY_DOWN):
            on_key_arrow_down(self.game_controller, self.game_state, pyxel.btn(pyxel.KEY_CTRL))
        elif pyxel.btnp(pyxel.KEY_UP):
            on_key_arrow_up(self.game_controller, self.game_state, pyxel.btn(pyxel.KEY_CTRL))
        elif pyxel.btnp(pyxel.KEY_LEFT):
            on_key_arrow_left(self.game_controller, self.game_state, pyxel.btn(pyxel.KEY_CTRL))
        elif pyxel.btnp(pyxel.KEY_RIGHT):
            on_key_arrow_right(self.game_controller, self.game_state, pyxel.btn(pyxel.KEY_CTRL))
        elif pyxel.btnp(pyxel.KEY_RETURN):
            on_key_return(self.game_controller, self.game_state)
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            on_mouse_button_right(self.game_state)
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            on_mouse_button_left(self.game_state)
        elif pyxel.btnp(pyxel.KEY_SHIFT):
            on_key_shift(self.game_state)
        elif pyxel.btnp(pyxel.KEY_C):
            on_key_c(self.game_state)
        elif pyxel.btnp(pyxel.KEY_F):
            on_key_f(self.game_controller, self.game_state)
        elif pyxel.btnp(pyxel.KEY_D):
            on_key_d(self.game_state)
        elif pyxel.btnp(pyxel.KEY_TAB):
            on_key_tab(self.game_state)
        elif pyxel.btnp(pyxel.KEY_SPACE):
            on_key_space(self.game_controller, self.game_state)
        elif pyxel.btnp(pyxel.KEY_M):
            on_key_m(self.game_state)
        elif pyxel.btnp(pyxel.KEY_S):
            on_key_s(self.game_state)
        elif pyxel.btnp(pyxel.KEY_N):
            on_key_n(self.game_controller, self.game_state)
        elif pyxel.btnp(pyxel.KEY_B):
            on_key_b(self.game_state)
        elif pyxel.btnp(pyxel.KEY_ESCAPE):
            on_key_escape(self.game_state)
        elif pyxel.btnp(pyxel.KEY_A):
            on_key_a(self.game_controller, self.game_state)
        elif pyxel.btnp(pyxel.KEY_J):
            on_key_j(self.game_state)
        elif pyxel.btnp(pyxel.KEY_X):
            on_key_x(self.game_state)
