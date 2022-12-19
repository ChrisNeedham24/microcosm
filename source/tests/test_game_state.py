import typing
import unittest

from source.foundation.models import GameConfig, Faction, Player
from source.game_management.game_state import GameState


class GameStateTest(unittest.TestCase):
    """
    The test class for game_state.py.
    """

    def setUp(self) -> None:
        """
        Initialise a standard GameState object before each test.
        """
        self.game_state = GameState()

    def test_gen_players(self):
        """
        Ensure that player are generated for a game according to the supplied game configuration.
        """
        test_config = GameConfig(5, Faction.NOCTURNE, True, False, True)

        self.assertFalse(self.game_state.players)
        self.game_state.gen_players(test_config)

        non_ai_players: typing.List[Player] = \
            list(filter(lambda player: player.name == "The Chosen One", self.game_state.players))
        self.assertEqual(1, len(non_ai_players))
        self.assertEqual(test_config.player_faction, non_ai_players[0].faction)
        self.assertEqual(test_config.player_count, len(self.game_state.players))


if __name__ == '__main__':
    unittest.main()
