import unittest
from unittest.mock import patch

from source.display.board import Board
from source.foundation.catalogue import Namer, UNIT_PLANS
from source.foundation.models import GameConfig, Faction, Unit, Player, Settlement
from source.game_management.movemaker import search_for_relics_or_move


class MovemakerTest(unittest.TestCase):
    """
    The test class for movemaker.py.
    """
    TEST_CONFIG = GameConfig(2, Faction.NOCTURNE, True, True, True)
    TEST_BOARD = Board(TEST_CONFIG, Namer())
    TEST_UNIT = Unit(1, UNIT_PLANS[0].total_stamina, (3, 4), False, UNIT_PLANS[0])
    TEST_UNIT_2 = Unit(5, 6, (7, 8), False, UNIT_PLANS[0])
    TEST_UNIT_3 = Unit(9, 10, (11, 12), False, UNIT_PLANS[0])
    TEST_PLAYER = Player("TesterMan", Faction.NOCTURNE, 0, 0, [], [TEST_UNIT], [], set(), set())
    TEST_SETTLEMENT = Settlement("Obstructionville", (0, 0), [], [], [])

    def setUp(self) -> None:
        """
        Generate the quads to use, locate a relic, and reset the test models.
        """
        self.TEST_BOARD.generate_quads(self.TEST_CONFIG.biome_clustering)
        self.QUADS = self.TEST_BOARD.quads
        # We need to find a relic quad before each test, because the quads are re-generated each time.
        self.relic_coords: (int, int) = -1, -1
        for i in range(2, 90):
            for j in range(2, 80):
                if self.QUADS[i][j].is_relic:
                    self.relic_coords = i, j
                    break
            if self.relic_coords[0] != -1:
                break
        # More than one relic can make the tests unreliable, so remove all others.
        for i in range(90):
            for j in range(80):
                if self.QUADS[i][j].is_relic and self.relic_coords != (i, j):
                    self.QUADS[i][j].is_relic = False
        self.TEST_UNIT.location = 3, 4
        self.TEST_UNIT.remaining_stamina = UNIT_PLANS[0].total_stamina
        # Position the other two units and settlement to be surrounding the relic, obstructing its access.
        self.TEST_UNIT_2.location = self.relic_coords[0] - 1, self.relic_coords[1]
        self.TEST_UNIT_3.location = self.relic_coords[0], self.relic_coords[1] + 1
        self.TEST_SETTLEMENT.location = self.relic_coords[0], self.relic_coords[1] - 1
        self.TEST_PLAYER.units = [self.TEST_UNIT]

    """
    Set blessing cases to test

    No available blessings
    Player requires wealth
    Player requires harvest
    Player requires zeal
    Player requires fortune
    Aggressive AI chooses unit
    Aggressive AI no units, takes ideal
    Defensive AI chooses strength
    Defensive AI no strength, takes ideal
    """

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_search_for_relics_success_left(self):
        """
        Ensure that when a relic is within range and to the left of a unit, the unit investigates and removes it.
        """
        self.TEST_UNIT.location = self.relic_coords[0] - 2, self.relic_coords[1]

        self.assertTrue(self.TEST_UNIT.remaining_stamina)
        self.assertTrue(self.QUADS[self.relic_coords[0]][self.relic_coords[1]].is_relic)
        search_for_relics_or_move(self.TEST_UNIT, self.QUADS, self.TEST_PLAYER, [], [], self.TEST_CONFIG)

        # The unit should have moved directly to the left of the relic, and the quad should no longer have a relic.
        self.assertTupleEqual((self.relic_coords[0] - 1, self.relic_coords[1]), self.TEST_UNIT.location)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertFalse(self.QUADS[self.relic_coords[0]][self.relic_coords[1]].is_relic)

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_search_for_relics_success_right(self):
        """
        Ensure that when a relic is within range and to the right of a unit, the unit investigates and removes it.
        """
        self.TEST_UNIT.location = self.relic_coords[0] + 2, self.relic_coords[1]

        self.assertTrue(self.TEST_UNIT.remaining_stamina)
        self.assertTrue(self.QUADS[self.relic_coords[0]][self.relic_coords[1]].is_relic)
        search_for_relics_or_move(self.TEST_UNIT, self.QUADS, self.TEST_PLAYER, [], [], self.TEST_CONFIG)

        # The unit should have moved directly to the right of the relic, and the quad should no longer have a relic.
        self.assertTupleEqual((self.relic_coords[0] + 1, self.relic_coords[1]), self.TEST_UNIT.location)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertFalse(self.QUADS[self.relic_coords[0]][self.relic_coords[1]].is_relic)

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_search_for_relics_obstructed(self):
        """
        Ensure that when the three options for movement for a unit to a relic within range are obstructed, the unit just
        moves randomly instead. The three things that can obstruct a relic are player units, AI units, and settlements.
        In this test, we surround the relic with one of each.
        """
        self.TEST_PLAYER.units.append(self.TEST_UNIT_2)
        self.TEST_UNIT.location = self.relic_coords[0] - 2, self.relic_coords[1]

        self.assertTrue(self.TEST_UNIT.remaining_stamina)
        self.assertTrue(self.QUADS[self.relic_coords[0]][self.relic_coords[1]].is_relic)
        search_for_relics_or_move(self.TEST_UNIT, self.QUADS, self.TEST_PLAYER, [self.TEST_UNIT_3],
                                  [self.TEST_SETTLEMENT], self.TEST_CONFIG)

        # Normally, the unit would move directly to the left of the relic, but it can't move there, and as such, the
        # quad should still have a relic.
        self.assertNotEqual((self.relic_coords[0] - 1, self.relic_coords[1]), self.TEST_UNIT.location)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertTrue(self.QUADS[self.relic_coords[0]][self.relic_coords[1]].is_relic)

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_search_for_relics_none_found(self):
        """
        Ensure that when there are no available relics, the unit moves randomly.
        """
        # Remove the last relic from the board.
        self.QUADS[self.relic_coords[0]][self.relic_coords[1]].is_relic = False

        self.assertTrue(self.TEST_UNIT.remaining_stamina)
        search_for_relics_or_move(self.TEST_UNIT, self.QUADS, self.TEST_PLAYER, [], [], self.TEST_CONFIG)
        # Make sure the unit exhausted its stamina.
        self.assertFalse(self.TEST_UNIT.remaining_stamina)

    """
    Make move cases to test / things to verify
    
    ---All in one test---
    Blessing is set
    Construction is set
    Construction is bought out in situations where it should be
    Settler is deployed
    Units are moved
    Units are sold
    
    ---Individual tests for deployment---
    Non-defensive AI auto-deploys garrisoned units
    Unit deployed when besieged
    Unit deployed when below max strength
    Unit deployed for defensive AI when not besieged and at max strength but garrison size of 4
    """


if __name__ == '__main__':
    unittest.main()
