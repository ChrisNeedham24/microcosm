import time

from source.foundation.catalogue import Namer
from source.display.menu import Menu
from source.game_management.movemaker import MoveMaker
from source.util.music_player import MusicPlayer


class GameController:
    """
    The class that governs the overall control of the game experience, such as Menu management, music playing
    and other utilities that are distinct from the game and board logic.
    """

    def __init__(self):
        """
        Initialises the Menu, music player and other utilities.
        """
        self.menu = Menu()

        self.last_time = time.time()
        self.last_turn_time: float

        self.music_player = MusicPlayer()
        self.music_player.play_menu_music()

        self.namer = Namer()
        self.move_maker = MoveMaker(self.namer)
