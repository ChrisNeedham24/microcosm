import typing
import unittest
from unittest.mock import MagicMock

from source.display.board import Board
from source.foundation.catalogue import Namer, UNIT_PLANS, get_heathen_plan
from source.foundation.models import GameConfig, Faction, Player, AIPlaystyle, AttackPlaystyle, ExpansionPlaystyle, \
    Unit, Heathen
from source.game_management.game_state import GameState
from source.game_management.movemaker import MoveMaker


class GameStateTest(unittest.TestCase):
    """
    The test class for game_state.py.
    """
    TEST_CONFIG = GameConfig(5, Faction.NOCTURNE, True, False, True)
    TEST_NAMER = Namer()
    TEST_UNIT = Unit(1, 2, (3, 4), False, UNIT_PLANS[0])
    TEST_HEATHEN = Heathen(40, 6, (3, 3), get_heathen_plan(1))

    def setUp(self) -> None:
        """
        Initialise a standard GameState object with players and a board before each test. Also reset the test models.
        """
        self.game_state = GameState()
        self.game_state.players = [
            Player("Infidel", Faction.INFIDELS, 0, 0, [], [self.TEST_UNIT], [], set(), set(),
                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)),
            Player("Concentrator", Faction.CONCENTRATED, 0, 0, [], [], [], set(), set(),
                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)),
            Player("Man", Faction.FRONTIERSMEN, 0, 0, [], [], [], set(), set(),
                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)),
            Player("Royal", Faction.IMPERIALS, 0, 0, [], [], [], set(), set(),
                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)),
        ]
        self.game_state.board = Board(self.TEST_CONFIG, self.TEST_NAMER)
        self.game_state.heathens = [self.TEST_HEATHEN]
        self.TEST_UNIT.location = 3, 4
        self.TEST_UNIT.health = 1
        self.TEST_HEATHEN.location = 3, 3
        self.TEST_HEATHEN.health = 40
        self.TEST_HEATHEN.remaining_stamina = 6

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

    def test_process_heathens_infidel(self):
        """
        Ensure that units owned by players of the Infidels faction are not attacked by heathens.
        """
        self.game_state.board.overlay.toggle_attack = MagicMock()

        self.assertFalse(self.game_state.players[0].quads_seen)
        self.game_state.process_heathens()

        # We make sure that an attack does not occur using the toggle_attack mock. This would normally be called because
        # the player being attacked is the first player, i.e. the human player, meaning an overlay is displayed to alert
        # them to the attack.
        self.game_state.board.overlay.toggle_attack.assert_not_called()
        self.assertFalse(self.TEST_HEATHEN.remaining_stamina)
        # We also check here that the Infidels player has their vision updated by the heathen's movement.
        self.assertTrue(self.game_state.players[0].quads_seen)

    def test_process_heathens_not_within_range(self):
        """
        Ensure that heathens move randomly when there are no units in range to attack.
        """
        # Move the test unit away from the heathen, and make the player a non-protected faction.
        self.TEST_UNIT.location = 50, 50
        self.game_state.players[0].faction = Faction.AGRICULTURISTS
        self.game_state.board.overlay.toggle_attack = MagicMock()

        self.game_state.process_heathens()

        # We make sure that an attack does not occur using the toggle_attack mock. This would normally be called because
        # the player being attacked is the first player, i.e. the human player, meaning an overlay is displayed to alert
        # them to the attack.
        self.game_state.board.overlay.toggle_attack.assert_not_called()
        self.assertFalse(self.TEST_HEATHEN.remaining_stamina)

    def test_process_heathens_too_much_health(self):
        """
        Ensure that heathens do not attack units that have too much more health than them.
        """
        # Increase the test unit's health, and make the player a non-protected faction.
        self.TEST_UNIT.health = 100
        self.game_state.players[0].faction = Faction.AGRICULTURISTS
        self.game_state.board.overlay.toggle_attack = MagicMock()

        self.game_state.process_heathens()

        # We make sure that an attack does not occur using the toggle_attack mock. This would normally be called because
        # the player being attacked is the first player, i.e. the human player, meaning an overlay is displayed to alert
        # them to the attack.
        self.game_state.board.overlay.toggle_attack.assert_not_called()
        self.assertFalse(self.TEST_HEATHEN.remaining_stamina)

    def test_process_heathens_attack_left_unit_killed(self):
        """
        Ensure that the correct state and overlay changes occur when a heathen attacks and kills a unit.
        """
        # Make the player a non-protected faction.
        self.game_state.players[0].faction = Faction.AGRICULTURISTS
        self.game_state.board.overlay.toggle_attack = MagicMock()
        self.game_state.board.selected_unit = self.game_state.players[0].units[0]
        self.game_state.board.overlay.toggle_unit = MagicMock()

        self.game_state.process_heathens()

        # Because the heathen was initially positioned below the unit, it should be moved to its left.
        self.assertTupleEqual((self.TEST_UNIT.location[0] - 1, self.TEST_UNIT.location[1]), self.TEST_HEATHEN.location)
        self.assertFalse(self.TEST_HEATHEN.remaining_stamina)
        self.game_state.board.overlay.toggle_attack.assert_called()
        # Because the unit was killed, the attacked player should no longer have any units.
        self.assertFalse(self.game_state.players[0].units)
        # Additionally, the unit overlay should be removed because the selected unit is no longer present.
        self.assertIsNone(self.game_state.board.selected_unit)
        self.game_state.board.overlay.toggle_unit.assert_called_with(None)
        # Make sure the heathen was not killed.
        self.assertTrue(self.game_state.heathens)

    def test_process_heathens_attack_right_heathen_killed(self):
        """
        Ensure that the correct state and overlay changes occur when a heathen attacks a unit, but is killed itself.
        """
        # Make the player a non-protected faction.
        self.game_state.players[0].faction = Faction.AGRICULTURISTS
        self.game_state.board.overlay.toggle_attack = MagicMock()
        # Move the heathen to the units right, and set up the healths so that the heathen will attack the unit, but die
        # nevertheless.
        self.TEST_HEATHEN.location = 5, 3
        self.TEST_UNIT.health = 50
        self.TEST_HEATHEN.health = 25

        self.game_state.process_heathens()

        # The heathen should have moved next to the unit, on the right.
        self.assertTupleEqual((self.TEST_UNIT.location[0] + 1, self.TEST_UNIT.location[1]), self.TEST_HEATHEN.location)
        self.assertFalse(self.TEST_HEATHEN.remaining_stamina)
        self.game_state.board.overlay.toggle_attack.assert_called()
        # Make sure the unit was not killed.
        self.assertTrue(self.game_state.players[0].units)
        # Because the heathen was killed, the game state should no longer have any heathens.
        self.assertFalse(self.game_state.heathens)

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
