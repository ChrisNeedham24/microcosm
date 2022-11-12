import random
import typing

from board import Board
from models import Player, Heathen


class GameState:
    """
    The class that holds the logical Microcosm game state, to determine the state of the current game.
    """
    def __init__(self):
        """
        Creates the initial game state.
        """
        self.board: typing.Optional[Board] = None
        self.players: typing.List[Player] = []
        self.heathens: typing.List[Heathen] = []

        self.on_menu = True
        self.game_started = False

        # The map begins at a random position.
        self.map_pos: (int, int) = random.randint(0, 76), random.randint(0, 68)
        self.turn = 1

        random.seed()
        # There will always be a 10-20 turn break between nights.
        self.until_night: int = random.randint(10, 20)
        # Also keep track of how many turns of night are left. If this is 0, it is daytime.
        self.nighttime_left = 0
