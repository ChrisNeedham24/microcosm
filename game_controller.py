import time

from catalogue import Namer
from menu import Menu
from movemaker import MoveMaker
from music_player import MusicPlayer


class GameController:
    """
    The class that governs the overall control of the game experience, such as Menu management, inputs, music playing
    and other utilities that are distinct from the game and board logic.
    """
    def __init__(self):
        """
        Initialises the game.
        """
        self.menu = Menu()

        self.last_time = time.time()

        self.music_player = MusicPlayer()
        self.music_player.play_menu_music()

        self.namer = Namer()
        self.move_maker = MoveMaker(self.namer)