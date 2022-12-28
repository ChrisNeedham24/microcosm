import typing
import unittest
from unittest.mock import MagicMock

from source.display.board import Board
from source.foundation.catalogue import Namer
from source.foundation.models import GameConfig, Faction, Player, AIPlaystyle, AttackPlaystyle, ExpansionPlaystyle
from source.game_management.game_state import GameState
from source.game_management.movemaker import MoveMaker


class GameStateTest(unittest.TestCase):
    """
    The test class for game_state.py.
    """
    TEST_CONFIG = GameConfig(5, Faction.NOCTURNE, True, False, True)
    TEST_NAMER = Namer()

    def setUp(self) -> None:
        """
        Initialise a standard GameState object with players and a board before each test.
        """
        self.game_state = GameState()
        self.game_state.players = [
            Player("Infidel", Faction.INFIDELS, 0, 0, [], [], [], set(), set(),
                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)),
            Player("Concentrator", Faction.CONCENTRATED, 0, 0, [], [], [], set(), set(),
                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)),
            Player("Man", Faction.FRONTIERSMEN, 0, 0, [], [], [], set(), set(),
                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)),
            Player("Royal", Faction.IMPERIALS, 0, 0, [], [], [], set(), set(),
                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)),
        ]
        self.game_state.board = Board(self.TEST_CONFIG, self.TEST_NAMER)

    def test_gen_players(self):
        """
        Ensure that players are generated for a game according to the supplied game configuration.
        """
        self.game_state.players = []
        self.game_state.gen_players(self.TEST_CONFIG)

        non_ai_players: typing.List[Player] = \
            list(filter(lambda player: player.name == "The Chosen One", self.game_state.players))
        self.assertEqual(1, len(non_ai_players))
        self.assertEqual(self.TEST_CONFIG.player_faction, non_ai_players[0].faction)
        self.assertEqual(self.TEST_CONFIG.player_count, len(self.game_state.players))

    def test_initialise_ais(self):
        """
        Ensure that AI players have their settlements correctly initialised.
        """
        # To begin with, make sure that the settlements are created at all.
        self.assertFalse(any(player.settlements for player in self.game_state.players))
        self.game_state.initialise_ais(self.TEST_NAMER)
        self.assertTrue(all(player.settlements for player in self.game_state.players))

        # The first player is of the Infidels faction, so their settlement should have no modifiers applied.
        self.assertEqual(100, self.game_state.players[0].settlements[0].strength)
        self.assertEqual(100, self.game_state.players[0].settlements[0].max_strength)
        self.assertEqual(50, self.game_state.players[0].settlements[0].satisfaction)

        # The second player is of the Concentrated faction, so their settlement should have double the strength.
        self.assertEqual(200, self.game_state.players[1].settlements[0].strength)
        self.assertEqual(200, self.game_state.players[1].settlements[0].max_strength)
        self.assertEqual(50, self.game_state.players[0].settlements[0].satisfaction)

        # The third player is of the Frontiersmen faction, so their settlement should have increased satisfaction.
        self.assertEqual(100, self.game_state.players[2].settlements[0].strength)
        self.assertEqual(100, self.game_state.players[2].settlements[0].max_strength)
        self.assertEqual(75, self.game_state.players[2].settlements[0].satisfaction)

        # The final player is of the Imperials faction, so their settlement should have half the strength.
        self.assertEqual(50, self.game_state.players[3].settlements[0].strength)
        self.assertEqual(50, self.game_state.players[3].settlements[0].max_strength)
        self.assertEqual(50, self.game_state.players[0].settlements[0].satisfaction)

    def test_process_ais(self):
        """
        Ensure that when processing AI turns, a move is made for each player.
        """
        test_movemaker = MoveMaker(self.TEST_NAMER)
        test_movemaker.make_move = MagicMock()

        self.game_state.process_ais(test_movemaker)
        self.assertEqual(len(self.game_state.players), test_movemaker.make_move.call_count)


if __name__ == '__main__':
    unittest.main()
