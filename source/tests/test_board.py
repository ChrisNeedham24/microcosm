import unittest
from unittest.mock import MagicMock

from source.display.board import Board, HelpOption
from source.foundation.catalogue import Namer, get_heathen_plan
from source.foundation.models import GameConfig, Faction, Quad, Biome, Player, Settlement, Unit, UnitPlan, Heathen, \
    DeployerUnit, DeployerUnitPlan


class BoardTest(unittest.TestCase):
    """
    The test class for board.py.
    """
    TEST_CONFIG = GameConfig(2, Faction.CONCENTRATED, True, True, True)
    TEST_NAMER = Namer()
    TEST_UPDATE_TIME = 2
    TEST_UPDATE_TIME_OVER = 4

    def setUp(self) -> None:
        """
        Instantiate a standard Board object with generated quads before each test. Also initialise the test models and
        save some relevant quad coordinates.
        """
        self.board = Board(self.TEST_CONFIG, self.TEST_NAMER)
        self.TEST_UNIT_PLAN = UnitPlan(100, 100, 2, "TestMan", None, 0, heals=True)
        self.TEST_DEPLOYER_UNIT_PLAN = DeployerUnitPlan(0, 50, 10, "Train", None, 0)
        self.TEST_UNIT = Unit(100, 2, (5, 5), False, self.TEST_UNIT_PLAN)
        self.TEST_UNIT_2 = Unit(100, 2, (8, 8), False, self.TEST_UNIT_PLAN)
        self.TEST_UNIT_3 = Unit(100, 10, (9, 9), False, self.TEST_UNIT_PLAN)
        self.TEST_DEPLOYER_UNIT = DeployerUnit(50, 5, (4, 4), False, self.TEST_DEPLOYER_UNIT_PLAN)
        self.TEST_DEPLOYER_UNIT_2 = DeployerUnit(40, 4, (3, 3), False, self.TEST_DEPLOYER_UNIT_PLAN)
        self.TEST_HEATHEN = Heathen(100, 2, (10, 10), get_heathen_plan(1))
        self.TEST_QUAD = Quad(Biome.MOUNTAIN, 0, 0, 0, 0, (7, 7))
        self.TEST_QUAD_2 = Quad(Biome.SEA, 0, 0, 0, 0, (6, 6))
        self.TEST_SETTLEMENT = Settlement("Test Town", (7, 7), [], [self.TEST_QUAD], [])
        self.TEST_ENEMY_SETTLEMENT = Settlement("Bad Town", (6, 6), [], [self.TEST_QUAD_2], [])
        self.TEST_PLAYER = Player("Mr. Tester", Faction.FUNDAMENTALISTS, 0,
                                  settlements=[self.TEST_SETTLEMENT], units=[self.TEST_UNIT])
        self.TEST_ENEMY_PLAYER = Player("Dr. Evil", Faction.INFIDELS, 0,
                                  settlements=[self.TEST_ENEMY_SETTLEMENT], units=[self.TEST_UNIT_2])
        # We need to find a relic quad before each test, because the quads are re-generated each time.
        self.relic_coords: (int, int) = -1, -1
        for i in range(90):
            for j in range(80):
                if self.board.quads[i][j].is_relic:
                    self.relic_coords = i, j
                    break
            if self.relic_coords[0] != -1:
                break

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

    def test_construction_without_clustering(self):
        """
        Ensure that board construction still functions correctly when biome clustering is disabled.
        """
        no_clustering_cfg = GameConfig(2, Faction.NOCTURNE, False, True, True)

        new_board = Board(no_clustering_cfg, self.TEST_NAMER)

        self.assertEqual(HelpOption.SETTLEMENT, new_board.current_help)
        self.assertFalse(new_board.help_time_bank)
        self.assertFalse(new_board.attack_time_bank)
        self.assertFalse(new_board.siege_time_bank)
        self.assertFalse(new_board.construction_prompt_time_bank)
        self.assertFalse(new_board.heal_time_bank)
        self.assertEqual(no_clustering_cfg, new_board.game_config)
        self.assertEqual(self.TEST_NAMER, new_board.namer)

        # Only 90 because it's a 2D array.
        self.assertEqual(90, len(new_board.quads))

        self.assertIsNone(new_board.quad_selected)
        self.assertTrue(new_board.overlay)
        self.assertIsNone(new_board.selected_settlement)
        self.assertFalse(new_board.deploying_army)
        self.assertIsNone(new_board.selected_unit)

    def test_construction_loading(self):
        """
        Ensure that the Board is constructed correctly, initialising class variables and using supplied quads.
        """
        # We can just have a single Quad here for testing.
        test_quads = [[
            Quad(Biome.MOUNTAIN, 1.0, 1.0, 1.0, 1.0, (0, 0))
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

    def test_left_click_deselect_quad(self):
        """
        Ensure that left-clicking deselects any currently-selected quad, no matter where on the screen is clicked.
        """
        test_quad = self.board.quads[0][0]
        test_quad.selected = True
        self.board.quad_selected = test_quad
        self.board.process_left_click(0, 0, False, self.TEST_PLAYER, (0, 0), [], [], [], [])
        self.assertFalse(test_quad.selected)
        self.assertIsNone(self.board.quad_selected)

    def test_left_click_new_settlement(self):
        """
        Ensure that new settlements are correctly created when a player with no settlements left-clicks on the board.
        """
        self.board.overlay.toggle_tutorial = MagicMock()
        self.board.overlay.toggle_settlement = MagicMock()

        test_player = Player("Mr. Agriculture", Faction.AGRICULTURISTS, 0)

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

        test_player = Player("Trying to concentrate", Faction.CONCENTRATED, 0)

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

        test_player = Player("Man of frontier", Faction.FRONTIERSMEN, 0)

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

        test_player = Player("The emperor", Faction.IMPERIALS, 0)

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

        test_quad = Quad(Biome.FOREST, 0, 0, 0, 0, (22, 22))
        test_settlement = Settlement("Tester", (22, 22), [], [test_quad], [])
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

    def test_left_click_select_settlement(self):
        """
        Ensure that settlements are successfully selected and their overlay displayed when left-clicked.
        """
        self.board.overlay.toggle_settlement = MagicMock()

        self.assertIsNone(self.board.selected_settlement)
        self.board.process_left_click(20, 20, True, self.TEST_PLAYER, (5, 5), [], [], [], [])
        self.assertEqual(self.TEST_SETTLEMENT, self.board.selected_settlement)
        self.board.overlay.toggle_settlement.assert_called_with(self.TEST_SETTLEMENT, self.TEST_PLAYER)

    def test_left_click_garrison_unit(self):
        """
        Ensure that units are successfully garrisoned in settlements when the unit's stamina is sufficient to reach the
        selected settlement.
        """
        self.board.overlay.toggle_unit = MagicMock()
        self.board.selected_unit = self.TEST_PLAYER.units[0]

        unit = self.TEST_PLAYER.units[0]
        initial_stamina = unit.remaining_stamina
        setl = self.TEST_PLAYER.settlements[0]
        # To begin with, the unit should not be garrisoned, and the settlement should have no units in its garrison.
        self.assertFalse(unit.garrisoned)
        self.assertFalse(setl.garrison)
        self.board.process_left_click(20, 20, True, self.TEST_PLAYER, (5, 5), [], [], [], [])
        # The unit should now be in the settlement's garrison, removed from the player's units, and deselected.
        self.assertLess(unit.remaining_stamina, initial_stamina)
        self.assertTrue(unit.garrisoned)
        self.assertTrue(setl.garrison)
        self.assertFalse(self.TEST_PLAYER.units)
        self.assertIsNone(self.board.selected_unit)
        self.board.overlay.toggle_unit.assert_called_with(None)

        self.board.overlay.toggle_unit.reset_mock()

        # However, let's try this again with a unit that is too far away from the settlement to reach it.
        far_away_unit = Unit(100, 2, (75, 75), False, self.TEST_UNIT_PLAN)
        self.TEST_PLAYER.units.append(far_away_unit)
        self.board.selected_unit = far_away_unit
        self.board.process_left_click(20, 20, True, self.TEST_PLAYER, (5, 5), [], [], [], [])
        # Rather than be garrisoned, the unit stays as-is, and the settlement remains with only the initial unit in its
        # garrison.
        self.assertFalse(far_away_unit.garrisoned)
        self.assertEqual(1, len(setl.garrison))
        self.assertTrue(self.TEST_PLAYER.units)
        # You may expect the unit to still be selected because it was not garrisoned. Not so, due to the fact that in
        # this case, the unit is instead deselected because an alternative quad is clicked where the unit cannot move
        # to.

    def test_left_click_add_passenger_to_deployer_unit(self):
        self.board.overlay.toggle_unit = MagicMock()
        self.TEST_PLAYER.units.append(self.TEST_DEPLOYER_UNIT)
        self.board.selected_unit = self.TEST_PLAYER.units[0]

        unit = self.TEST_PLAYER.units[0]
        initial_stamina = unit.remaining_stamina
        dep_unit = self.TEST_DEPLOYER_UNIT

        self.assertFalse(dep_unit.passengers)
        self.board.process_left_click(5, 5, True, self.TEST_PLAYER, (4, 4), [], [], [], [])
        self.assertLess(unit.remaining_stamina, initial_stamina)
        self.assertIn(unit, dep_unit.passengers)
        self.assertNotIn(unit, self.TEST_PLAYER.units)
        self.assertIsNone(self.board.selected_unit)
        self.board.overlay.toggle_unit.assert_called_with(None)

    def test_left_click_add_deployer_unit_passenger_to_deployer_unit(self):
        self.TEST_PLAYER.units.extend([self.TEST_DEPLOYER_UNIT, self.TEST_DEPLOYER_UNIT_2])
        self.board.selected_unit = self.TEST_DEPLOYER_UNIT_2
        self.board.overlay.toggle_unit = MagicMock()
        self.board.overlay.update_unit = MagicMock()

        initial_unit = self.TEST_DEPLOYER_UNIT_2
        initial_stamina = initial_unit.remaining_stamina
        unit_to_board = self.TEST_DEPLOYER_UNIT

        self.assertFalse(unit_to_board.passengers)
        self.board.process_left_click(5, 5, True, self.TEST_PLAYER, (4, 4), [],
                                      [self.TEST_DEPLOYER_UNIT, self.TEST_DEPLOYER_UNIT_2], [], [])
        self.assertEqual(initial_unit.remaining_stamina, initial_stamina)
        self.assertNotIn(initial_unit, unit_to_board.passengers)
        self.assertIn(initial_unit, self.TEST_PLAYER.units)
        self.assertEqual(unit_to_board, self.board.selected_unit)
        self.board.overlay.toggle_unit.assert_not_called()
        self.board.overlay.update_unit.assert_called_with(unit_to_board)

    def test_left_click_add_passenger_to_max_capacity_deployer_unit(self):
        self.TEST_UNIT.plan.heals = False
        self.TEST_DEPLOYER_UNIT.plan.max_capacity = 0
        self.board.overlay.toggle_unit = MagicMock()
        self.board.overlay.update_unit = MagicMock()
        self.TEST_PLAYER.units.append(self.TEST_DEPLOYER_UNIT)
        self.board.selected_unit = self.TEST_PLAYER.units[0]

        unit = self.TEST_PLAYER.units[0]
        initial_stamina = unit.remaining_stamina
        dep_unit = self.TEST_DEPLOYER_UNIT

        self.assertFalse(dep_unit.passengers)
        self.board.process_left_click(5, 5, True, self.TEST_PLAYER, (4, 4), [], self.TEST_PLAYER.units, [], [])
        self.assertEqual(unit.remaining_stamina, initial_stamina)
        self.assertNotIn(unit, dep_unit.passengers)
        self.assertIn(unit, self.TEST_PLAYER.units)
        self.assertEqual(dep_unit, self.board.selected_unit)
        self.board.overlay.toggle_unit.assert_not_called()
        self.board.overlay.update_unit.assert_called_with(dep_unit)

    def test_left_click_add_passenger_to_deployer_unit_too_far_away(self):
        self.TEST_UNIT.plan.heals = False
        self.TEST_UNIT.location = 50, 50
        self.board.overlay.toggle_unit = MagicMock()
        self.board.overlay.update_unit = MagicMock()
        self.TEST_PLAYER.units.append(self.TEST_DEPLOYER_UNIT)
        self.board.selected_unit = self.TEST_PLAYER.units[0]

        unit = self.TEST_PLAYER.units[0]
        initial_stamina = unit.remaining_stamina
        dep_unit = self.TEST_DEPLOYER_UNIT

        self.assertFalse(dep_unit.passengers)
        self.board.process_left_click(5, 5, True, self.TEST_PLAYER, (4, 4), [], self.TEST_PLAYER.units, [], [])
        self.assertEqual(unit.remaining_stamina, initial_stamina)
        self.assertNotIn(unit, dep_unit.passengers)
        self.assertIn(unit, self.TEST_PLAYER.units)
        self.assertEqual(dep_unit, self.board.selected_unit)
        self.board.overlay.toggle_unit.assert_not_called()
        self.board.overlay.update_unit.assert_called_with(dep_unit)

    def test_left_click_deploy(self):
        """
        Ensure that units are deployed correctly when clicking a quad adjacent to a settlement.
        """
        self.board.overlay.toggle_deployment = MagicMock()
        self.board.overlay.toggle_settlement = MagicMock()
        self.board.overlay.toggle_unit = MagicMock()

        # Set up the scenario in which we have selected a settlement with a unit in its garrison, and we are deploying
        # said unit.
        self.board.deploying_army = True
        self.board.selected_settlement = self.TEST_PLAYER.settlements[0]
        unit = self.TEST_PLAYER.units.pop()
        self.TEST_PLAYER.settlements[0].garrison.append(unit)
        unit.garrisoned = True

        # Click a quad not adjacent to the settlement - this should fail.
        self.board.process_left_click(50, 20, True, self.TEST_PLAYER, (5, 5), [], [], [], [])
        # As expected, the unit is still garrisoned, and the deployment is still ongoing with no state changes or
        # toggles of overlays.
        self.assertTrue(unit.garrisoned)
        self.assertFalse(self.TEST_PLAYER.units)
        self.assertFalse(self.TEST_PLAYER.quads_seen)
        self.assertTrue(self.board.deploying_army)
        self.assertIsNone(self.board.selected_unit)
        self.board.overlay.toggle_deployment.assert_not_called()
        self.assertEqual(self.TEST_SETTLEMENT, self.board.selected_settlement)
        self.board.overlay.toggle_settlement.assert_not_called()
        self.board.overlay.toggle_unit.assert_not_called()

        # Now if we click an adjacent quad, updates should occur.
        self.board.process_left_click(30, 20, True, self.TEST_PLAYER, (5, 5), [], [], [], [])
        # The unit should no longer be garrisoned, and should be located where the click occurred.
        self.assertFalse(unit.garrisoned)
        self.assertEqual((8, 7), unit.location)
        # The player should also have the unit in their possession, not the settlement's, and their seen quads should be
        # updated.
        self.assertTrue(self.TEST_PLAYER.units)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        # The deployment should also be concluded, updating state to show the new unit as selected, and toggling a few
        # overlays.
        self.assertFalse(self.board.deploying_army)
        self.assertEqual(unit, self.board.selected_unit)
        self.board.overlay.toggle_deployment.assert_called()
        self.assertIsNone(self.board.selected_settlement)
        self.board.overlay.toggle_settlement.assert_called_with(None, self.TEST_PLAYER)
        self.board.overlay.toggle_unit.assert_called_with(unit)

    def test_left_click_deploy_from_unit(self):
        """
        Ensure that units are deployed correctly when clicking a quad adjacent to a deployer unit.
        """
        self.board.overlay.toggle_deployment = MagicMock()
        self.board.overlay.update_unit = MagicMock()

        # Set up the scenario in which we have selected a deployer unit with a passenger unit, and we are deploying
        # said passenger unit.
        self.board.deploying_army_from_unit = True
        self.board.selected_unit = self.TEST_DEPLOYER_UNIT
        self.TEST_DEPLOYER_UNIT.passengers = [self.TEST_UNIT, self.TEST_UNIT_3]
        self.TEST_PLAYER.units = [self.TEST_DEPLOYER_UNIT]
        self.board.overlay.unit_passengers_idx = 1
        self.board.overlay.show_unit_passengers = True

        # Click a quad not adjacent to the deployer unit - this should fail.
        self.board.process_left_click(20, 5, True, self.TEST_PLAYER, (5, 5), [], [], [], [])
        # As expected, the unit is still a passenger, and the deployment is still ongoing with no state changes or
        # toggles of overlays.
        self.assertListEqual([self.TEST_UNIT, self.TEST_UNIT_3], self.TEST_PLAYER.units[0].passengers)
        self.assertListEqual([self.TEST_DEPLOYER_UNIT], self.TEST_PLAYER.units)
        self.assertFalse(self.TEST_PLAYER.quads_seen)
        self.assertTrue(self.board.deploying_army_from_unit)
        self.assertEqual(1, self.board.overlay.unit_passengers_idx)
        self.assertTrue(self.board.overlay.show_unit_passengers)
        self.assertEqual(self.TEST_DEPLOYER_UNIT, self.board.selected_unit)
        self.board.overlay.toggle_deployment.assert_not_called()
        self.board.overlay.update_unit.assert_not_called()

        # Now if we click an adjacent quad, updates should occur.
        self.board.process_left_click(5, 5, True, self.TEST_PLAYER, (5, 5), [], [], [], [])
        # The unit should be located where the click occurred.
        self.assertTupleEqual((5, 5), self.TEST_UNIT_3.location)
        # The player should also have the unit in their possession, not the deployer unit's, and their seen quads should
        # be updated.
        self.assertListEqual([self.TEST_DEPLOYER_UNIT, self.TEST_UNIT_3], self.TEST_PLAYER.units)
        self.assertListEqual([self.TEST_UNIT], self.TEST_DEPLOYER_UNIT.passengers)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        # The deployment should also be concluded, updating state to show the new unit as selected, and toggling a few
        # overlays.
        self.assertFalse(self.board.deploying_army_from_unit)
        self.assertEqual(0, self.board.overlay.unit_passengers_idx)
        self.assertFalse(self.board.overlay.show_unit_passengers)
        self.assertEqual(self.TEST_UNIT_3, self.board.selected_unit)
        self.board.overlay.toggle_deployment.assert_called()
        self.board.overlay.update_unit.assert_called_with(self.TEST_UNIT_3)

    def test_left_click_select_heathen(self):
        """
        Ensure that heathens are appropriately selected when clicked on.
        """
        self.board.overlay.toggle_unit = MagicMock()

        self.board.process_left_click(45, 45, True, self.TEST_PLAYER, (5, 5), [self.TEST_HEATHEN], [], [], [])
        self.assertEqual(self.TEST_HEATHEN, self.board.selected_unit)
        self.board.overlay.toggle_unit.assert_called_with(self.TEST_HEATHEN)

    def test_left_click_attack_already_acted(self):
        """
        Ensure that when a unit has already acted, clicking on an adjacent enemy unit does not initiate an attack.
        """
        self.TEST_UNIT.has_acted = True
        # Move the unit next to TEST_UNIT_2, which is at (8, 8).
        self.TEST_UNIT.location = (7, 8)
        self.board.selected_unit = self.TEST_UNIT
        self.board.overlay.toggle_attack = MagicMock()

        self.board.process_left_click(15, 15, True, self.TEST_PLAYER, (7, 7), [], [self.TEST_UNIT, self.TEST_UNIT_2],
                                      [self.TEST_PLAYER, self.TEST_ENEMY_PLAYER], [])
        self.assertIsNone(self.board.selected_unit)
        self.board.overlay.toggle_attack.assert_not_called()

    def test_left_click_attack_itself(self):
        """
        Ensure that when the selected unit is clicked on, the unit does not somehow attack itself.
        """
        self.board.selected_unit = self.TEST_UNIT
        self.board.overlay.toggle_attack = MagicMock()

        self.board.process_left_click(5, 5, True, self.TEST_PLAYER, (5, 5), [],
                                      [self.TEST_UNIT], [self.TEST_PLAYER], [])
        self.assertEqual(self.TEST_UNIT, self.board.selected_unit)
        self.board.overlay.toggle_attack.assert_not_called()

    def test_left_click_attack_too_far_away(self):
        """
        Ensure that when an enemy unit outside the selected unit's range is clicked on, an attack is not initiated.
        """
        self.board.selected_unit = self.TEST_UNIT
        self.board.overlay.toggle_attack = MagicMock()

        # TEST_UNIT is at (5, 5) and TEST_UNIT_2 is being clicked on here, which is at (8, 8). This is clearly too far
        # away.
        self.board.process_left_click(35, 35, True, self.TEST_PLAYER, (5, 5), [], [self.TEST_UNIT, self.TEST_UNIT_2],
                                      [self.TEST_PLAYER, self.TEST_ENEMY_PLAYER], [])
        self.assertEqual(self.TEST_UNIT, self.board.selected_unit)
        self.board.overlay.toggle_attack.assert_not_called()

    def test_left_click_attack_no_casualties(self):
        """
        Ensure that the correct state and overlay updates occur when an attack between units occurs with no casualties.
        """
        # Move the unit next to TEST_UNIT_2, which is at (8, 8).
        self.TEST_UNIT.location = (7, 8)
        self.board.selected_unit = self.TEST_UNIT
        self.board.overlay.toggle_attack = MagicMock()

        self.board.process_left_click(15, 15, True, self.TEST_PLAYER, (7, 7), [], [self.TEST_UNIT, self.TEST_UNIT_2],
                                      [self.TEST_PLAYER, self.TEST_ENEMY_PLAYER], [])
        self.assertEqual(self.TEST_UNIT, self.board.selected_unit)
        # The overlay should be displayed and its time bank reset.
        self.board.overlay.toggle_attack.assert_called()
        self.assertFalse(self.board.attack_time_bank)
        # The units themselves should also still be associated with their players.
        self.assertIn(self.TEST_UNIT, self.TEST_PLAYER.units)
        self.assertIn(self.TEST_UNIT_2, self.TEST_ENEMY_PLAYER.units)

    def test_left_click_attack_attacker_killed(self):
        """
        Ensure that the correct state and overlay updates occur when an attack between units occurs and the attacker
        player unit is killed.
        """
        # Move the unit next to TEST_UNIT_2, which is at (8, 8). Also reduce its health to make its death certain.
        self.TEST_UNIT.location = (7, 8)
        self.TEST_UNIT.health = 1
        self.board.selected_unit = self.TEST_UNIT
        self.board.overlay.toggle_attack = MagicMock()
        self.board.overlay.toggle_unit = MagicMock()

        self.board.process_left_click(15, 15, True, self.TEST_PLAYER, (7, 7), [], [self.TEST_UNIT, self.TEST_UNIT_2],
                                      [self.TEST_PLAYER, self.TEST_ENEMY_PLAYER], [])
        # The unit should have been removed from the player's units.
        self.assertNotIn(self.TEST_UNIT, self.TEST_PLAYER.units)
        # The unit should also no longer be selected, and its overlay removed.
        self.assertIsNone(self.board.selected_unit)
        self.board.overlay.toggle_unit.assert_called_with(None)
        # The attack overlay should however be displayed and its time bank reset.
        self.board.overlay.toggle_attack.assert_called()
        self.assertFalse(self.board.attack_time_bank)
        # Make sure the enemy unit is still alive.
        self.assertIn(self.TEST_UNIT_2, self.TEST_ENEMY_PLAYER.units)

    def test_left_click_attack_heathen_killed(self):
        """
        Ensure that the correct state and overlay updates occur when an attack between unit and heathen occurs and the
        heathen is killed.
        """
        # Move the unit next to TEST_HEATHEN, which is at (10, 10).
        self.TEST_UNIT.location = (9, 10)
        # Reduce the heathen's health to make its death certain.
        self.TEST_HEATHEN.health = 1
        # We need to pre-define the list of heathens because the board processing method will remove the heathen from
        # this list if it is killed.
        heathen_list = [self.TEST_HEATHEN]
        self.board.selected_unit = self.TEST_UNIT
        self.board.overlay.toggle_attack = MagicMock()

        self.board.process_left_click(15, 15, True, self.TEST_PLAYER, (9, 9),
                                      heathen_list, [self.TEST_UNIT], [self.TEST_PLAYER], [])
        # The heathen should have been removed from our list, as expected.
        self.assertFalse(heathen_list)
        self.assertEqual(self.TEST_UNIT, self.board.selected_unit)
        # The attack overlay should be displayed and its time bank reset.
        self.board.overlay.toggle_attack.assert_called()
        self.assertFalse(self.board.attack_time_bank)
        # Make sure the player unit is still alive.
        self.assertIn(self.TEST_UNIT, self.TEST_PLAYER.units)

    def test_left_click_attack_defender_killed(self):
        """
        Ensure that the correct state and overlay updates occur when an attack occurs between units and the defender is
        killed.
        """
        # Move the unit next to TEST_UNIT_2, which is at (8, 8).
        self.TEST_UNIT.location = (7, 8)
        # Reduce the enemy unit's health to make its death certain.
        self.TEST_UNIT_2.health = 1
        self.board.selected_unit = self.TEST_UNIT
        self.board.overlay.toggle_attack = MagicMock()

        self.board.process_left_click(15, 15, True, self.TEST_PLAYER, (7, 7), [], [self.TEST_UNIT, self.TEST_UNIT_2],
                                      [self.TEST_PLAYER, self.TEST_ENEMY_PLAYER], [])
        # The enemy unit should have been removed from its player's units.
        self.assertNotIn(self.TEST_UNIT_2, self.TEST_ENEMY_PLAYER.units)
        self.assertEqual(self.TEST_UNIT, self.board.selected_unit)
        # The attack overlay should be displayed and its time bank reset.
        self.board.overlay.toggle_attack.assert_called()
        self.assertFalse(self.board.attack_time_bank)
        # Make sure the player unit is still alive.
        self.assertIn(self.TEST_UNIT, self.TEST_PLAYER.units)

    def test_left_click_attack_heal(self):
        """
        Ensure that the correct state and overlay updates occur when an adjacent friendly unit is clicked on when a
        healer unit is selected.
        """
        self.TEST_PLAYER.units.append(self.TEST_UNIT_3)
        # Move the unit next to TEST_UNIT_3, which is at (9, 9).
        self.TEST_UNIT.location = (8, 9)
        original_health = 1
        self.TEST_UNIT_3.health = original_health
        self.board.selected_unit = self.TEST_UNIT
        self.board.overlay.toggle_heal = MagicMock()

        self.board.process_left_click(15, 15, True, self.TEST_PLAYER, (8, 8), [],
                                      [self.TEST_UNIT, self.TEST_UNIT_3], [self.TEST_PLAYER], [])
        # The friendly unit should have had its health increased.
        self.assertGreater(self.TEST_UNIT_3.health, original_health)
        # The heal overlay should be displayed and its time bank reset.
        self.board.overlay.toggle_heal.assert_called()
        self.assertFalse(self.board.heal_time_bank)
        self.assertEqual(self.TEST_UNIT, self.board.selected_unit)

    def test_left_click_attack_select_other_unit(self):
        """
        Ensure that clicking on friendly units changes the currently-selected unit to them.
        """
        self.TEST_PLAYER.units.append(self.TEST_UNIT_3)
        self.board.selected_unit = self.TEST_UNIT
        self.board.overlay.update_unit = MagicMock()

        self.board.process_left_click(15, 15, True, self.TEST_PLAYER, (8, 8), [],
                                      [self.TEST_UNIT, self.TEST_UNIT_3], [self.TEST_PLAYER], [])
        self.assertEqual(self.TEST_UNIT_3, self.board.selected_unit)
        self.board.overlay.update_unit.assert_called_with(self.TEST_UNIT_3)

    def test_left_click_setl_click(self):
        """
        Ensure that when a selected unit clicks on an adjacent settlement, it toggles the settlement click overlay.
        """
        self.board.overlay.toggle_setl_click = MagicMock()
        self.board.selected_unit = self.TEST_PLAYER.units[0]

        # To begin with, move the selected unit far from an enemy settlement. Since it is too far away, if it clicks on
        # the settlement, nothing should appear.
        self.board.selected_unit.location = (50, 50)
        self.board.process_left_click(12, 12, True, self.TEST_PLAYER, (5, 5), [], [],
                                      [self.TEST_PLAYER, self.TEST_ENEMY_PLAYER], [self.TEST_ENEMY_SETTLEMENT])
        self.board.overlay.toggle_setl_click.assert_not_called()

        # However, if we reset the unit's position to be adjacent to the enemy settlement, the overlay should
        # successfully toggle when the settlement is clicked on.
        self.board.selected_unit.location = (5, 5)
        self.board.process_left_click(12, 12, True, self.TEST_PLAYER, (5, 5), [], [],
                                      [self.TEST_PLAYER, self.TEST_ENEMY_PLAYER], [self.TEST_ENEMY_SETTLEMENT])
        self.board.overlay.toggle_setl_click.assert_called_with(self.TEST_ENEMY_SETTLEMENT, self.TEST_ENEMY_PLAYER)

    def test_left_click_select_unit(self):
        """
        Ensure that units are selected when clicked on.
        """
        self.board.overlay.toggle_unit = MagicMock()

        self.assertIsNone(self.board.selected_unit)
        self.board.process_left_click(5, 5, True, self.TEST_PLAYER, (5, 5), [], self.TEST_PLAYER.units, [], [])
        self.assertEqual(self.TEST_UNIT, self.board.selected_unit)
        self.board.overlay.toggle_unit.assert_called_with(self.TEST_UNIT)

    def test_left_click_move_heathen(self):
        """
        Ensure that when a heathen is selected, clicking on an adjacent quad does not move it.
        """
        self.board.selected_unit = self.TEST_HEATHEN

        self.assertTupleEqual((10, 10), self.TEST_HEATHEN.location)
        self.board.process_left_click(55, 50, True, self.TEST_PLAYER, (5, 5), [], self.TEST_PLAYER.units, [], [])
        # The heathen should not have moved and should no longer be selected.
        self.assertTupleEqual((10, 10), self.TEST_HEATHEN.location)
        self.assertIsNone(self.board.selected_unit)

    def test_left_click_move_other_player_unit(self):
        """
        Ensure that when another player's unit is selected, clicking on a quad that it is within its range does not move
        the unit.
        """
        self.board.selected_unit = self.TEST_UNIT_2

        self.assertTupleEqual((8, 8), self.TEST_UNIT_2.location)
        self.board.process_left_click(40, 30, True, self.TEST_PLAYER, (5, 5), [],
                                      [self.TEST_UNIT, self.TEST_UNIT_2], [], [])
        # The unit should not have moved and should no longer be selected.
        self.assertTupleEqual((8, 8), self.TEST_UNIT_2.location)
        self.assertIsNone(self.board.selected_unit)

    def test_left_click_move_on_top_of_other_unit(self):
        """
        Ensure that when a player's unit is selected, clicking on a quad that is within its range, but is occupied by
        another of the player's units, does not move the unit.
        """
        self.TEST_PLAYER.units.append(self.TEST_UNIT_3)

        self.assertTupleEqual((9, 9), self.TEST_UNIT_3.location)
        self.board.process_left_click(5, 5, True, self.TEST_PLAYER, (5, 5), [],
                                      [self.TEST_UNIT, self.TEST_UNIT_3], [], [])
        # The original unit should not have moved and the other player unit should now be selected.
        self.assertTupleEqual((9, 9), self.TEST_UNIT_3.location)
        self.assertEqual(self.TEST_UNIT, self.board.selected_unit)

    def test_left_click_move_unit_on_top_of_enemy_settlement(self):
        """
        Ensure that when a player's unit is selected, clicking on a quad that is within its range, but is occupied by an
        enemy settlement, does not move the unit.
        """
        self.board.selected_unit = self.TEST_UNIT
        self.board.overlay.toggle_setl_click = MagicMock()

        self.assertTupleEqual((5, 5), self.TEST_UNIT.location)
        self.board.process_left_click(15, 15, True, self.TEST_PLAYER, (5, 5), [], [],
                                      [self.TEST_PLAYER, self.TEST_ENEMY_PLAYER], [self.TEST_ENEMY_SETTLEMENT])
        # The unit should not have moved and the settlement click overlay should have been toggled.
        self.assertTupleEqual((5, 5), self.TEST_UNIT.location)
        self.board.overlay.toggle_setl_click.assert_called()

    def test_left_click_move_unit_on_top_of_relic(self):
        """
        Ensure that when a player's unit is selected, clicking on an adjacent quad that is occupied by a relic does not
        move the unit.
        """
        self.board.selected_unit = self.TEST_UNIT
        # Position the unit next to a relic.
        self.board.selected_unit.location = (self.relic_coords[1], self.relic_coords[0] + 1)

        self.board.process_left_click(5, 5, True, self.TEST_PLAYER, (self.relic_coords[1], self.relic_coords[0]), [],
                                      [], [], [])
        # The unit should not have moved, and instead the relic should have been investigated.
        self.assertTupleEqual((self.relic_coords[1], self.relic_coords[0] + 1), self.board.selected_unit.location)
        self.assertFalse(self.board.quads[self.relic_coords[0]][self.relic_coords[1]].is_relic)

    def test_left_click_move_unit_not_enough_stamina(self):
        """
        Ensure that when a player's unit is selected, clicking on a quad outside its range does not move it.
        """
        self.board.selected_unit = self.TEST_UNIT

        self.assertTupleEqual((5, 5), self.TEST_UNIT.location)
        self.board.process_left_click(50, 50, True, self.TEST_PLAYER, (4, 4), [], [], [], [])
        self.assertTupleEqual((5, 5), self.TEST_UNIT.location)

    def test_left_click_move_unit(self):
        """
        Ensure that when a player's unit is selected, clicking on a quad within its range moves it there.
        """
        self.board.selected_unit = self.TEST_UNIT

        self.assertTupleEqual((5, 5), self.TEST_UNIT.location)
        self.board.process_left_click(5, 5, True, self.TEST_PLAYER, (4, 4), [], [], [], [])
        self.assertTupleEqual((4, 4), self.TEST_UNIT.location)

    def test_left_click_move_unit_into_siege(self):
        """
        Ensure that when a player's unit is moved within range of an enemy settlement currently under siege, the unit's
        state is correctly updated.
        """
        self.TEST_ENEMY_SETTLEMENT.besieged = True
        self.TEST_PLAYER.units.append(self.TEST_UNIT_3)
        self.board.selected_unit = self.TEST_UNIT_3

        self.assertTupleEqual((9, 9), self.TEST_UNIT_3.location)
        self.board.process_left_click(25, 15, True, self.TEST_PLAYER, (5, 5), [], [],
                                      [self.TEST_PLAYER, self.TEST_ENEMY_PLAYER], [self.TEST_ENEMY_SETTLEMENT])
        # The unit should have moved next to the settlement under siege and the unit should now be besieging.
        self.assertTupleEqual((7, 6), self.TEST_UNIT_3.location)
        self.assertTrue(self.TEST_UNIT_3.besieging)

    def test_left_click_relic(self):
        """
        Ensure that when a unit clicks on an adjacent relic, it loses its relic status and brings up the investigation
        overlay.
        """
        self.board.overlay.toggle_investigation = MagicMock()
        self.board.selected_unit = self.TEST_PLAYER.units[0]

        # Teleport the unit to be far from the pre-determined relic coordinates.
        self.board.selected_unit.location = 0, 0
        if self.relic_coords[0] <= 1 or self.relic_coords[1] <= 1:
            self.board.selected_unit.location = 80, 80
        # Because the unit is too far away from the relic, it and the overlay should be unaffected by the click.
        self.assertTrue(self.board.quads[self.relic_coords[0]][self.relic_coords[1]].is_relic)
        self.board.process_left_click(5, 5, True, self.TEST_PLAYER, (self.relic_coords[1], self.relic_coords[0]), [],
                                      [], [], [])
        self.assertTrue(self.board.quads[self.relic_coords[0]][self.relic_coords[1]].is_relic)
        self.board.overlay.toggle_investigation.assert_not_called()

        # However, if we teleport the unit to be right next to the relic, the click should result in the relic
        # disappearing and the investigation overlay being toggled.
        self.board.selected_unit.location = (self.relic_coords[1], self.relic_coords[0] + 1)
        self.assertTrue(self.board.quads[self.relic_coords[0]][self.relic_coords[1]].is_relic)
        self.board.process_left_click(5, 5, True, self.TEST_PLAYER, (self.relic_coords[1], self.relic_coords[0]), [],
                                      [], [], [])
        self.assertFalse(self.board.quads[self.relic_coords[0]][self.relic_coords[1]].is_relic)
        # Note that we cannot specify the expected arguments due to the fact that each investigation result is random.
        self.board.overlay.toggle_investigation.assert_called()

    def test_left_click_deselect_unit(self):
        """
        Ensure that when a unit is selected and the player clicks elsewhere, the unit is deselected.
        """
        self.board.overlay.toggle_unit = MagicMock()
        self.board.selected_unit = self.TEST_UNIT

        self.board.process_left_click(50, 50, True, self.TEST_PLAYER, (5, 5), [], [], [], [])
        self.assertIsNone(self.board.selected_unit)
        self.board.overlay.toggle_unit.assert_called_with(None)

    def test_handle_new_settlement(self):
        """
        Ensure that settlements are successfully created and selected, and the corresponding settler units are destroyed
        when handling new settlements.
        """
        self.board.overlay.toggle_unit = MagicMock()
        self.board.overlay.toggle_settlement = MagicMock()

        # Move the test unit to occupy the same quad as any existing settlement, meaning it should not be able to found
        # a new one.
        self.TEST_UNIT.location = self.TEST_PLAYER.settlements[0].location
        self.board.selected_unit = self.TEST_UNIT

        # As expected, the settlement should not be founded.
        self.assertEqual(1, len(self.TEST_PLAYER.settlements))
        self.board.handle_new_settlement(self.TEST_PLAYER)
        self.assertEqual(1, len(self.TEST_PLAYER.settlements))

        # Move the unit back to its original location.
        self.board.selected_unit.location = (5, 5)

        self.assertEqual(1, len(self.TEST_PLAYER.units))
        self.board.handle_new_settlement(self.TEST_PLAYER)
        # The new settlement should have been created with the standard specifications.
        self.assertEqual(2, len(self.TEST_PLAYER.settlements))
        new_setl = self.TEST_PLAYER.settlements[1]
        self.assertEqual(50, new_setl.satisfaction)
        self.assertEqual(100, new_setl.strength)
        self.assertEqual(100, new_setl.max_strength)
        # The settler unit should no longer exist nor be selected, and the unit overlay should be toggled off.
        self.assertFalse(self.TEST_PLAYER.units)
        self.assertIsNone(self.board.selected_unit)
        self.board.overlay.toggle_unit.assert_called_with(None)
        # The new settlement should also be selected and its overlay displayed.
        self.assertEqual(new_setl, self.board.selected_settlement)
        self.board.overlay.toggle_settlement.assert_called_with(new_setl, self.TEST_PLAYER)

    def test_handle_new_settlement_frontiersmen(self):
        """
        Ensure that new settlements are created correctly for players of the Frontiersmen faction.
        """
        self.board.overlay.toggle_unit = MagicMock()
        self.board.overlay.toggle_settlement = MagicMock()

        self.board.selected_unit = self.TEST_UNIT
        self.TEST_PLAYER.faction = Faction.FRONTIERSMEN

        self.assertEqual(1, len(self.TEST_PLAYER.units))
        self.board.handle_new_settlement(self.TEST_PLAYER)
        self.assertEqual(2, len(self.TEST_PLAYER.settlements))
        new_setl = self.TEST_PLAYER.settlements[1]
        # The fundamental difference here is that we expect the satisfaction to be elevated.
        self.assertEqual(75, new_setl.satisfaction)
        self.assertEqual(100, new_setl.strength)
        self.assertEqual(100, new_setl.max_strength)
        self.assertFalse(self.TEST_PLAYER.units)
        self.assertIsNone(self.board.selected_unit)
        self.board.overlay.toggle_unit.assert_called_with(None)
        self.assertEqual(new_setl, self.board.selected_settlement)
        self.board.overlay.toggle_settlement.assert_called_with(new_setl, self.TEST_PLAYER)

    def test_handle_new_settlement_imperials(self):
        """
        Ensure that new settlements are created correctly for players of the Imperials faction.
        """
        self.board.overlay.toggle_unit = MagicMock()
        self.board.overlay.toggle_settlement = MagicMock()

        self.board.selected_unit = self.TEST_UNIT
        self.TEST_PLAYER.faction = Faction.IMPERIALS

        self.assertEqual(1, len(self.TEST_PLAYER.units))
        self.board.handle_new_settlement(self.TEST_PLAYER)
        self.assertEqual(2, len(self.TEST_PLAYER.settlements))
        new_setl = self.TEST_PLAYER.settlements[1]
        self.assertEqual(50, new_setl.satisfaction)
        # The fundamental difference here is that we expect the strength to be reduced.
        self.assertEqual(50, new_setl.strength)
        self.assertEqual(50, new_setl.max_strength)
        self.assertFalse(self.TEST_PLAYER.units)
        self.assertIsNone(self.board.selected_unit)
        self.board.overlay.toggle_unit.assert_called_with(None)
        self.assertEqual(new_setl, self.board.selected_settlement)
        self.board.overlay.toggle_settlement.assert_called_with(new_setl, self.TEST_PLAYER)


if __name__ == '__main__':
    unittest.main()
