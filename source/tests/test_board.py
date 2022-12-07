import unittest
from unittest.mock import MagicMock

from source.display.board import Board, HelpOption
from source.foundation.catalogue import Namer
from source.foundation.models import GameConfig, Faction, Quad, Biome


class BoardTest(unittest.TestCase):
    """
    The test class for board.py
    """
    TEST_CONFIG = GameConfig(2, Faction.CONCENTRATED, True, True, True)
    TEST_NAMER = Namer()
    TEST_UPDATE_TIME = 2
    TEST_UPDATE_TIME_OVER = 4

    def setUp(self) -> None:
        """
        Instantiate a standard Board object with generated quads before each test.
        """
        self.board = Board(self.TEST_CONFIG, self.TEST_NAMER)

    def test_construction(self):
        """
        Ensure that the Board is constructed correctly, initialising class variables and generating quads.
        """
        self.assertEqual(HelpOption.SETTLEMENT, self.board.current_help)
        self.assertFalse(self.board.help_time_bank)
        self.assertFalse(self.board.attack_time_bank)
        self.assertFalse(self.board.siege_time_bank)
        self.assertFalse(self.board.construction_prompt_time_bank)
        self.assertFalse(self.board.heal_time_bank)
        self.assertEqual(self.TEST_CONFIG, self.board.game_config)
        self.assertEqual(self.TEST_NAMER, self.board.namer)

        # Only 90 because it's a 2D array.
        self.assertEqual(90, len(self.board.quads))

        self.assertIsNone(self.board.quad_selected)
        self.assertTrue(self.board.overlay)
        self.assertIsNone(self.board.selected_settlement)
        self.assertFalse(self.board.deploying_army)
        self.assertIsNone(self.board.selected_unit)

    def test_construction_loading(self):
        """
        Ensure that the Board is constructed correctly, initialising class variables and using supplied quads.
        """
        # We can just have a single Quad here for testing.
        test_quads = [[
            Quad(Biome.MOUNTAIN, 1.0, 1.0, 1.0, 1.0)
        ]]

        board = Board(self.TEST_CONFIG, self.TEST_NAMER, test_quads)

        self.assertEqual(HelpOption.SETTLEMENT, board.current_help)
        self.assertFalse(board.help_time_bank)
        self.assertFalse(board.attack_time_bank)
        self.assertFalse(board.siege_time_bank)
        self.assertFalse(board.construction_prompt_time_bank)
        self.assertFalse(board.heal_time_bank)
        self.assertEqual(self.TEST_CONFIG, board.game_config)
        self.assertEqual(self.TEST_NAMER, board.namer)

        # Since we supplied quads ourselves, these should be used.
        self.assertEqual(1, len(board.quads))

        self.assertIsNone(board.quad_selected)
        self.assertTrue(board.overlay)
        self.assertIsNone(board.selected_settlement)
        self.assertFalse(board.deploying_army)
        self.assertIsNone(board.selected_unit)

    def test_update_help(self):
        """
        Ensure that the help time bank and text are appropriately updated when the Board object is updated with elapsed
        time.
        """
        self.assertFalse(self.board.help_time_bank)
        self.assertEqual(HelpOption.SETTLEMENT, self.board.current_help)

        self.board.update(self.TEST_UPDATE_TIME)

        # Time has passed, but not enough to switch the help text.
        self.assertEqual(self.TEST_UPDATE_TIME, self.board.help_time_bank)
        self.assertEqual(HelpOption.SETTLEMENT, self.board.current_help)

        self.board.update(self.TEST_UPDATE_TIME)

        # Now, the time should be reset and the text should have changed.
        self.assertFalse(self.board.help_time_bank)
        self.assertEqual(HelpOption.UNIT, self.board.current_help)

        # Iterate through the remaining text options and ensure that they cycle through as expected.
        self.board.update(self.TEST_UPDATE_TIME_OVER)
        self.assertFalse(self.board.help_time_bank)
        self.assertEqual(HelpOption.OVERLAY, self.board.current_help)
        self.board.update(self.TEST_UPDATE_TIME_OVER)
        self.assertFalse(self.board.help_time_bank)
        self.assertEqual(HelpOption.PAUSE, self.board.current_help)
        self.board.update(self.TEST_UPDATE_TIME_OVER)
        self.assertFalse(self.board.help_time_bank)
        self.assertEqual(HelpOption.END_TURN, self.board.current_help)
        self.board.update(self.TEST_UPDATE_TIME_OVER)
        self.assertFalse(self.board.help_time_bank)
        self.assertEqual(HelpOption.SETTLEMENT, self.board.current_help)

    def test_update_attack(self):
        """
        Ensure that the attack time bank and overlay are appropriately updated when the Board object is updated with
        elapsed time.
        """
        # Mock out the relevant functions.
        self.board.overlay.is_attack = MagicMock(return_value=False)
        self.board.overlay.is_setl_attack = MagicMock(return_value=False)
        self.board.overlay.toggle_attack = MagicMock()
        self.board.overlay.toggle_setl_attack = MagicMock()

        # The bank should not have been updated since the attack overlay is not in view.
        self.assertFalse(self.board.attack_time_bank)
        self.board.update(self.TEST_UPDATE_TIME)
        self.assertFalse(self.board.attack_time_bank)

        self.board.overlay.is_attack.return_value = True
        # Now that we've set the attack overlay to be in view, the bank should be updated.
        self.board.update(self.TEST_UPDATE_TIME)
        self.assertEqual(self.TEST_UPDATE_TIME, self.board.attack_time_bank)

        self.board.overlay.is_attack.return_value = False
        self.board.overlay.is_setl_attack.return_value = True
        # This time, the settlement attack overlay is in view instead, but this still updates the bank, exceeding the
        # limit, and toggling the settlement attack overlay, making it disappear. The time bank is also reset.
        self.board.update(self.TEST_UPDATE_TIME)
        self.board.overlay.toggle_setl_attack.assert_called_with(None)
        self.assertFalse(self.board.attack_time_bank)

        self.board.overlay.is_setl_attack.return_value = False
        self.board.overlay.is_attack.return_value = True
        # Returning to viewing the attack overlay, the limit is once again exceeded, toggling the attack overlay to
        # disappear and maintaining the time bank at zero.
        self.board.update(self.TEST_UPDATE_TIME_OVER)
        self.board.overlay.toggle_attack.assert_called_with(None)
        self.assertFalse(self.board.attack_time_bank)

    def test_update_siege(self):
        """
        Ensure that the siege time bank and overlay are appropriately updated when the Board object is updated with
        elapsed time.
        """
        # Mock out the two relevant functions.
        self.board.overlay.is_siege_notif = MagicMock(return_value=False)
        self.board.overlay.toggle_siege_notif = MagicMock()

        # The bank should not have been updated since the siege overlay is not in view.
        self.assertFalse(self.board.siege_time_bank)
        self.board.update(self.TEST_UPDATE_TIME)
        self.assertFalse(self.board.siege_time_bank)

        self.board.overlay.is_siege_notif.return_value = True
        # Now that we've set the siege overlay to be in view, the bank should be updated.
        self.board.update(self.TEST_UPDATE_TIME)
        self.assertEqual(self.TEST_UPDATE_TIME, self.board.siege_time_bank)

        # Updating again exceeds the limit, toggling the overlay and resetting the time bank.
        self.board.update(self.TEST_UPDATE_TIME)
        self.board.overlay.toggle_siege_notif.assert_called_with(None, None)
        self.assertFalse(self.board.siege_time_bank)


if __name__ == '__main__':
    unittest.main()
