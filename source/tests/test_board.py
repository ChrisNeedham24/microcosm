import unittest
from unittest.mock import MagicMock

from source.display.board import Board, HelpOption
from source.foundation.catalogue import Namer
from source.foundation.models import GameConfig, Faction, Quad, Biome, Player, Settlement


class BoardTest(unittest.TestCase):
    """
    The test class for board.py
    """
    TEST_CONFIG = GameConfig(2, Faction.CONCENTRATED, True, True, True)
    TEST_NAMER = Namer()
    TEST_UPDATE_TIME = 2
    TEST_UPDATE_TIME_OVER = 4
    TEST_PLAYER = Player("Mr. Tester", Faction.FUNDAMENTALISTS, 0, 0, [], [], [], set(), set())

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

    def test_update_construction(self):
        """
        Ensure that the construction time bank and text are appropriately updated when the Board object is updated with
        elapsed time.
        """
        # Mock out the relevant functions.
        self.board.overlay.is_setl = MagicMock(return_value=False)
        self.board.selected_settlement = MagicMock()
        self.board.selected_settlement.current_work = None

        # The bank should not have been updated since the settlement overlay is not in view.
        self.assertFalse(self.board.construction_prompt_time_bank)
        self.board.update(self.TEST_UPDATE_TIME)
        self.assertFalse(self.board.construction_prompt_time_bank)

        self.board.overlay.is_setl.return_value = True
        # Now that we've set the settlement overlay to be in view, the bank should be updated.
        self.board.update(self.TEST_UPDATE_TIME)
        self.assertEqual(self.TEST_UPDATE_TIME, self.board.construction_prompt_time_bank)

        # Updating again exceeds the limit, changing the prompt and resetting the time bank.
        self.assertFalse(self.board.overlay.show_auto_construction_prompt)
        self.board.update(self.TEST_UPDATE_TIME)
        self.assertTrue(self.board.overlay.show_auto_construction_prompt)
        self.assertFalse(self.board.construction_prompt_time_bank)

    def test_update_heal(self):
        """
        Ensure that the heal time bank and overlay are appropriately updated when the Board object is updated with
        elapsed time.
        """
        # Mock out the two relevant functions.
        self.board.overlay.is_heal = MagicMock(return_value=False)
        self.board.overlay.toggle_heal = MagicMock()

        # The bank should not have been updated since the heal overlay is not in view.
        self.assertFalse(self.board.heal_time_bank)
        self.board.update(self.TEST_UPDATE_TIME)
        self.assertFalse(self.board.heal_time_bank)

        self.board.overlay.is_heal.return_value = True
        # Now that we've set the heal overlay to be in view, the bank should be updated.
        self.board.update(self.TEST_UPDATE_TIME)
        self.assertEqual(self.TEST_UPDATE_TIME, self.board.heal_time_bank)

        # Updating again exceeds the limit, toggling the overlay and resetting the time bank.
        self.board.update(self.TEST_UPDATE_TIME)
        self.board.overlay.toggle_heal.assert_called_with(None)
        self.assertFalse(self.board.siege_time_bank)

    def test_right_click(self):
        """
        Ensure that right-clicking quads behaves as expected.
        """
        # We're going to target the quad at (7, 7).
        self.assertFalse(self.board.quads[7][7].selected)
        self.board.process_right_click(20, 20, (5, 5))
        self.assertTrue(self.board.quads[7][7].selected)
        self.assertEqual(self.board.quads[7][7], self.board.quad_selected)

        # Let's right click the same quad again.
        self.board.process_right_click(20, 20, (5, 5))
        self.assertFalse(self.board.quads[7][7].selected)
        self.assertIsNone(self.board.quad_selected)

        # And once more.
        self.board.process_right_click(20, 20, (5, 5))
        self.assertTrue(self.board.quads[7][7].selected)
        self.assertEqual(self.board.quads[7][7], self.board.quad_selected)

        # Now, if we right click on another quad, it should be selected and the previously selected quad should be
        # deselected.
        self.board.process_right_click(28, 28, (5, 5))
        self.assertTrue(self.board.quads[8][8].selected)
        self.assertFalse(self.board.quads[7][7].selected)
        self.assertEqual(self.board.quads[8][8], self.board.quad_selected)

    def test_right_click_obscured(self):
        """
        Ensure that when the board is obscured, right-clicking has no effect.
        """
        self.board.overlay.is_standard = MagicMock(return_value=True)

        # There should be no quads selected to start with.
        self._verify_no_quads_selected()

        # Theoretically, this is a valid position, in the middle of the window. It would equate to the quad at (22, 22).
        self.board.process_right_click(100, 100, (10, 10))

        # Despite being a valid position, the above quad (and all others) should remain unselected due to the board
        # being obscured.
        self._verify_no_quads_selected()

    def test_right_click_out_of_bounds(self):
        """
        Ensure that when the player right-clicks outside the bounds of the board, no quads are selected.
        """
        # There should be no quads selected to start with.
        self._verify_no_quads_selected()

        # Click at an invalid X and valid Y position.
        self.board.process_right_click(0, 100, (10, 10))
        self._verify_no_quads_selected()

        # Click at a valid X and an invalid Y position.
        self.board.process_right_click(100, 0, (10, 10))
        self._verify_no_quads_selected()

        # Click at invalid X and Y positions.
        self.board.process_right_click(200, 200, (10, 10))
        self._verify_no_quads_selected()

    def _verify_no_quads_selected(self):
        """
        A helper method that checks all quads on the board, and asserts that they are not selected.
        """
        for quad_row in self.board.quads:
            for quad in quad_row:
                self.assertFalse(quad.selected)

    def test_left_click_new_settlement(self):
        """
        Ensure that new settlements are correctly created when a player with no settlements left-clicks on the board.
        """
        self.board.overlay.toggle_tutorial = MagicMock()
        self.board.overlay.toggle_settlement = MagicMock()

        test_player = Player("Mr. Agriculture", Faction.AGRICULTURISTS, 0, 0, [], [], [], set(), set())

        self.board.process_left_click(100, 100, False, test_player, (10, 10), [], [], [], [])
        # The player should now have a settlement, seen quads, and should no longer be seeing the tutorial overlay.
        self.assertTrue(test_player.settlements)
        self.assertTrue(test_player.quads_seen)
        self.board.overlay.toggle_tutorial.assert_called()
        new_setl = test_player.settlements[0]
        # The new settlement should also be selected, and in view in the settlement overlay.
        self.assertEqual(new_setl, self.board.selected_settlement)
        self.board.overlay.toggle_settlement.assert_called_with(new_setl, test_player)

        # The new settlement should have standard strength and satisfaction, since the player isn't of a faction that
        # has bonuses or penalties for these.
        self.assertEqual(100, new_setl.strength)
        self.assertEqual(100, new_setl.max_strength)
        self.assertEqual(50, new_setl.satisfaction)

        test_player = Player("Trying to concentrate", Faction.CONCENTRATED, 0, 0, [], [], [], set(), set())

        self.board.process_left_click(100, 100, False, test_player, (10, 10), [], [], [], [])
        self.assertTrue(test_player.settlements)
        self.assertTrue(test_player.quads_seen)
        self.board.overlay.toggle_tutorial.assert_called()
        new_setl = test_player.settlements[0]
        self.assertEqual(new_setl, self.board.selected_settlement)
        self.board.overlay.toggle_settlement.assert_called_with(new_setl, test_player)

        # Since the test player is now of the Concentrated faction, the settlement strength should be doubled, but the
        # starting satisfaction should remain as standard.
        self.assertEqual(200, new_setl.strength)
        self.assertEqual(200, new_setl.max_strength)
        self.assertEqual(50, new_setl.satisfaction)

        test_player = Player("Man of frontier", Faction.FRONTIERSMEN, 0, 0, [], [], [], set(), set())

        self.board.process_left_click(100, 100, False, test_player, (10, 10), [], [], [], [])
        self.assertTrue(test_player.settlements)
        self.assertTrue(test_player.quads_seen)
        self.board.overlay.toggle_tutorial.assert_called()
        new_setl = test_player.settlements[0]
        self.assertEqual(new_setl, self.board.selected_settlement)
        self.board.overlay.toggle_settlement.assert_called_with(new_setl, test_player)

        # Since the test player is now a Frontiersman, the settlement strength should be standard, but the satisfaction
        # should be increased.
        self.assertEqual(100, new_setl.strength)
        self.assertEqual(100, new_setl.max_strength)
        self.assertEqual(75, new_setl.satisfaction)

        test_player = Player("The emperor", Faction.IMPERIALS, 0, 0, [], [], [], set(), set())

        self.board.process_left_click(100, 100, False, test_player, (10, 10), [], [], [], [])
        self.assertTrue(test_player.settlements)
        self.assertTrue(test_player.quads_seen)
        self.board.overlay.toggle_tutorial.assert_called()
        new_setl = test_player.settlements[0]
        self.assertEqual(new_setl, self.board.selected_settlement)
        self.board.overlay.toggle_settlement.assert_called_with(new_setl, test_player)

        # Since the test player is now an Imperial, the settlement strength should be reduced, but the satisfaction
        # should be standard.
        self.assertEqual(50, new_setl.strength)
        self.assertEqual(50, new_setl.max_strength)
        self.assertEqual(50, new_setl.satisfaction)

    def test_left_click_deselect_settlement(self):
        """
        Ensure that left-clicking while a settlement is selected deselects the settlement (unless clicking directly on
        the settlement).
        """
        self.board.overlay.toggle_settlement = MagicMock()

        test_settlement = Settlement("Tester", (22, 22), [], [], [])
        self.board.selected_settlement = test_settlement

        # Since the coordinates of (100, 100) and the map position (10, 10) come out to the quad at (22, 22), our
        # settlement should still be selected, since it's being clicked on.
        self.board.process_left_click(100, 100, True, self.TEST_PLAYER, (10, 10), [], [], [], [])
        self.assertIsNotNone(self.board.selected_settlement)
        self.board.overlay.toggle_settlement.assert_not_called()

        # However, if we now click elsewhere, the settlement should be deselected and the overlay toggled off.
        self.board.process_left_click(150, 150, True, self.TEST_PLAYER, (10, 10), [], [], [], [])
        self.assertIsNone(self.board.selected_settlement)
        self.board.overlay.toggle_settlement.assert_called_with(None, self.TEST_PLAYER)

    # TODO tests for left click - obscured, quad select reset


if __name__ == '__main__':
    unittest.main()
