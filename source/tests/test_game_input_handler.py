import typing
import unittest
from unittest.mock import MagicMock, patch

from source.display.board import Board
from source.display.menu import SetupOption, WikiOption
from source.foundation.catalogue import Namer, BLESSINGS, UNIT_PLANS, get_available_improvements, \
    get_available_unit_plans, PROJECTS
from source.foundation.models import GameConfig, Faction, OverlayType, ConstructionMenu, Improvement, ImprovementType, \
    Effect, Project, ProjectType, UnitPlan, Player, Settlement, Unit, Construction, CompletedConstruction
from source.game_management.game_controller import GameController
from source.game_management.game_input_handler import on_key_arrow_down, on_key_arrow_up, on_key_arrow_left, \
    on_key_arrow_right, on_key_shift, on_key_f, on_key_d, on_key_s, on_key_n, on_key_a, on_key_c, on_key_tab, \
    on_key_escape, on_key_m, on_key_j, on_key_space, on_key_b
from source.game_management.game_state import GameState


class GameInputHandlerTest(unittest.TestCase):
    """
    The test class for game_input_handler.py.
    """
    TEST_UNIT = Unit(1, 1, (40, 40), True, UNIT_PLANS[0])
    TEST_UNIT_2 = Unit(2, 2, (50, 50), False, UNIT_PLANS[0])
    TEST_UNIT_NO_STAMINA = Unit(3, 0, (60, 60), False, UNIT_PLANS[0])
    TEST_UNIT_BESIEGING = Unit(4, 4, (70, 70), False, UNIT_PLANS[0], besieging=True)
    TEST_SETTLEMENT = Settlement("TestTown", (40, 40), [], [], [])
    TEST_SETTLEMENT_2 = Settlement("TestCity", (50, 50), [], [], [])
    TEST_SETTLEMENT_WITH_WORK = Settlement("Busyville", (60, 60), [], [], [], current_work=Construction(UNIT_PLANS[0]))
    PLAYER_WEALTH = 1000
    TEST_PLAYER = Player("Tester", Faction.NOCTURNE, 0, PLAYER_WEALTH,
                         [TEST_SETTLEMENT, TEST_SETTLEMENT_2, TEST_SETTLEMENT_WITH_WORK], [TEST_UNIT], [], set(), set())

    @patch("source.game_management.game_controller.MusicPlayer")
    def setUp(self, _: MagicMock) -> None:
        """
        Set up the GameController and GameState objects to be used as parameters in the test functions. Also instantiate
        the Board object for the GameState and reset test models. Note that we also mock out the MusicPlayer class that
        is used when constructing the GameController. This is because it will try to play music if not mocked.
        :param _: The unused MusicPlayer mock.
        """
        self.game_controller = GameController()
        self.game_state = GameState()
        self.game_state.board = Board(GameConfig(4, Faction.NOCTURNE, True, True, True), Namer())
        self.game_state.on_menu = False
        self.game_state.players = [self.TEST_PLAYER]
        self.TEST_PLAYER.wealth = self.PLAYER_WEALTH
        self.TEST_PLAYER.units = [self.TEST_UNIT]
        self.TEST_PLAYER.settlements = [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2, self.TEST_SETTLEMENT_WITH_WORK]
        self.TEST_PLAYER.faction = Faction.NOCTURNE
        self.TEST_SETTLEMENT.garrison = []
        self.TEST_SETTLEMENT.current_work = None
        self.TEST_SETTLEMENT_WITH_WORK.current_work = Construction(UNIT_PLANS[0])
        self.TEST_SETTLEMENT_WITH_WORK.garrison = []

    def test_arrow_down_menu(self):
        """
        Ensure that the correct method is called when pressing the down arrow key while on the menu.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.navigate = MagicMock()
        on_key_arrow_down(self.game_controller, self.game_state, False)
        self.game_controller.menu.navigate.assert_called_with(down=True)

    def test_arrow_down_construction(self):
        """
        Ensure that the correct method is called when pressing the down arrow key while viewing the construction
        overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.CONSTRUCTION]
        self.game_state.board.overlay.navigate_constructions = MagicMock()
        on_key_arrow_down(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_constructions.assert_called_with(down=True)

    def test_arrow_down_blessing(self):
        """
        Ensure that the correct method is called when pressing the down arrow key while viewing the blessing overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.BLESSING]
        self.game_state.board.overlay.navigate_blessings = MagicMock()
        on_key_arrow_down(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_blessings.assert_called_with(down=True)

    def test_arrow_down_settlement_click(self):
        """
        Ensure that the correct method is called when pressing the down arrow key while viewing the settlement click
        overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.SETL_CLICK]
        self.game_state.board.overlay.navigate_setl_click = MagicMock()
        on_key_arrow_down(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_setl_click.assert_called_with(down=True)

    def test_arrow_down_controls(self):
        """
        Ensure that the correct toggle occurs when pressing the down arrow key while viewing the controls overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.CONTROLS]
        self.assertFalse(self.game_state.board.overlay.show_additional_controls)
        on_key_arrow_down(self.game_controller, self.game_state, False)
        self.assertTrue(self.game_state.board.overlay.show_additional_controls)

    def test_arrow_down_pause(self):
        """
        Ensure that the correct method is called when pressing the down arrow key while viewing the pause overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.PAUSE]
        self.game_state.board.overlay.navigate_pause = MagicMock()
        on_key_arrow_down(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_pause.assert_called_with(down=True)

    def test_arrow_down_standard(self):
        """
        Ensure that the correct method is called when pressing the down arrow key while viewing the standard overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.STANDARD]
        self.game_state.board.overlay.navigate_standard = MagicMock()
        on_key_arrow_down(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_standard.assert_called_with(down=True)

    def test_arrow_down_map(self):
        """
        Ensure that the correct map panning occurs when pressing the down arrow key while no obscuring overlay is
        displayed.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.remove_warning_if_possible = MagicMock()
        pos_x, pos_y = self.game_state.map_pos = (5, 5)

        # Only one quad of movement should occur.
        on_key_arrow_down(self.game_controller, self.game_state, False)
        self.assertTupleEqual((pos_x, pos_y + 1), self.game_state.map_pos)

        # When pressing the control key, five quads of movement should occur.
        on_key_arrow_down(self.game_controller, self.game_state, True)
        self.assertTupleEqual((pos_x, pos_y + 6), self.game_state.map_pos)

    def test_arrow_up_menu(self):
        """
        Ensure that the correct method is called when pressing the up arrow key while on the menu.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.navigate = MagicMock()
        on_key_arrow_up(self.game_controller, self.game_state, False)
        self.game_controller.menu.navigate.assert_called_with(up=True)

    def test_arrow_up_construction(self):
        """
        Ensure that the correct method is called when pressing the up arrow key while viewing the construction
        overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.CONSTRUCTION]
        self.game_state.board.overlay.navigate_constructions = MagicMock()
        on_key_arrow_up(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_constructions.assert_called_with(down=False)

    def test_arrow_up_blessing(self):
        """
        Ensure that the correct method is called when pressing the up arrow key while viewing the blessing overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.BLESSING]
        self.game_state.board.overlay.navigate_blessings = MagicMock()
        on_key_arrow_up(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_blessings.assert_called_with(down=False)

    def test_arrow_up_settlement_click(self):
        """
        Ensure that the correct method is called when pressing the up arrow key while viewing the settlement click
        overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.SETL_CLICK]
        self.game_state.board.overlay.navigate_setl_click = MagicMock()
        on_key_arrow_up(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_setl_click.assert_called_with(up=True)

    def test_arrow_up_controls(self):
        """
        Ensure that the correct toggle occurs when pressing the up arrow key while viewing the controls overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.CONTROLS]
        self.game_state.board.overlay.show_additional_controls = True
        on_key_arrow_up(self.game_controller, self.game_state, False)
        self.assertFalse(self.game_state.board.overlay.show_additional_controls)

    def test_arrow_up_pause(self):
        """
        Ensure that the correct method is called when pressing the up arrow key while viewing the pause overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.PAUSE]
        self.game_state.board.overlay.navigate_pause = MagicMock()
        on_key_arrow_up(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_pause.assert_called_with(down=False)

    def test_arrow_up_standard(self):
        """
        Ensure that the correct method is called when pressing the up arrow key while viewing the standard overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.STANDARD]
        self.game_state.board.overlay.navigate_standard = MagicMock()
        on_key_arrow_up(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_standard.assert_called_with(down=False)

    def test_arrow_up_map(self):
        """
        Ensure that the correct map panning occurs when pressing the up arrow key while no obscuring overlay is
        displayed.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.remove_warning_if_possible = MagicMock()
        pos_x, pos_y = self.game_state.map_pos = (5, 5)

        on_key_arrow_up(self.game_controller, self.game_state, False)
        self.assertTupleEqual((pos_x, pos_y - 1), self.game_state.map_pos)

        on_key_arrow_up(self.game_controller, self.game_state, True)
        self.assertTupleEqual((pos_x, pos_y - 6), self.game_state.map_pos)

    def test_arrow_left_menu(self):
        """
        Ensure that the correct method is called when pressing the left arrow key while on the menu.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.navigate = MagicMock()
        on_key_arrow_left(self.game_controller, self.game_state, False)
        self.game_controller.menu.navigate.assert_called_with(left=True)

    def test_arrow_left_construction(self):
        """
        Ensure that the correct change in view occurs when pressing the left arrow key while viewing the construction
        overlay.
        """
        test_improvement = Improvement(ImprovementType.ECONOMICAL, 0, "Te", "st", Effect(), None)
        test_project = Project(ProjectType.ECONOMICAL, "Te", "st")

        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.CONSTRUCTION]
        self.game_state.board.overlay.current_construction_menu = ConstructionMenu.PROJECTS

        # Because the player has no available constructions, pressing left does nothing as there is no improvements menu
        # to be viewed.
        on_key_arrow_left(self.game_controller, self.game_state, False)
        self.assertEqual(ConstructionMenu.PROJECTS, self.game_state.board.overlay.current_construction_menu)
        self.assertIsNone(self.game_state.board.overlay.selected_construction)

        self.game_state.board.overlay.available_constructions = [test_improvement]

        # Now that an available construction has been assigned, the improvements menu should be viewable.
        on_key_arrow_left(self.game_controller, self.game_state, False)
        self.assertEqual(ConstructionMenu.IMPROVEMENTS, self.game_state.board.overlay.current_construction_menu)
        self.assertEqual(test_improvement, self.game_state.board.overlay.selected_construction)

        self.game_state.board.overlay.current_construction_menu = ConstructionMenu.UNITS
        self.game_state.board.overlay.available_projects = [test_project]

        # From the units menu, pressing left should bring us to the projects menu.
        on_key_arrow_left(self.game_controller, self.game_state, False)
        self.assertEqual(ConstructionMenu.PROJECTS, self.game_state.board.overlay.current_construction_menu)
        self.assertEqual(test_project, self.game_state.board.overlay.selected_construction)

    def test_arrow_left_settlement_click(self):
        """
        Ensure that the correct method is called when pressing the left arrow key while viewing the settlement click
        overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.SETL_CLICK]
        self.game_state.board.overlay.navigate_setl_click = MagicMock()
        on_key_arrow_left(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_setl_click.assert_called_with(left=True)

    def test_arrow_left_map(self):
        """
        Ensure that the correct map panning occurs when pressing the left arrow key while no obscuring overlay is
        displayed.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.remove_warning_if_possible = MagicMock()
        pos_x, pos_y = self.game_state.map_pos = (5, 5)

        on_key_arrow_left(self.game_controller, self.game_state, False)
        self.assertTupleEqual((pos_x - 1, pos_y), self.game_state.map_pos)

        on_key_arrow_left(self.game_controller, self.game_state, True)
        self.assertTupleEqual((pos_x - 6, pos_y), self.game_state.map_pos)

    def test_arrow_right_menu(self):
        """
        Ensure that the correct method is called when pressing the right arrow key while on the menu.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.navigate = MagicMock()
        on_key_arrow_right(self.game_controller, self.game_state, False)
        self.game_controller.menu.navigate.assert_called_with(right=True)

    def test_arrow_right_construction(self):
        """
        Ensure that the correct change in view occurs when pressing the right arrow key while viewing the construction
        overlay.
        """
        test_project = Project(ProjectType.ECONOMICAL, "Te", "st")
        test_unit_plan = UnitPlan(0, 0, 0, "Test", None, 0)

        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.CONSTRUCTION]
        self.game_state.board.overlay.current_construction_menu = ConstructionMenu.IMPROVEMENTS
        self.game_state.board.overlay.available_projects = [test_project]

        # Pressing the right arrow key while viewing improvements should take us to projects.
        on_key_arrow_right(self.game_controller, self.game_state, False)
        self.assertEqual(ConstructionMenu.PROJECTS, self.game_state.board.overlay.current_construction_menu)
        self.assertEqual(test_project, self.game_state.board.overlay.selected_construction)

        self.game_state.board.overlay.available_unit_plans = [test_unit_plan]

        # Pressing the right arrow key while viewing projects should display units, while also resetting the boundaries
        # for said units.
        on_key_arrow_right(self.game_controller, self.game_state, False)
        self.assertEqual(ConstructionMenu.UNITS, self.game_state.board.overlay.current_construction_menu)
        self.assertEqual(test_unit_plan, self.game_state.board.overlay.selected_construction)
        self.assertTupleEqual((0, 5), self.game_state.board.overlay.unit_plan_boundaries)

    def test_arrow_right_settlement_click(self):
        """
        Ensure that the correct method is called when pressing the right arrow key while viewing the settlement click
        overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.SETL_CLICK]
        self.game_state.board.overlay.navigate_setl_click = MagicMock()
        on_key_arrow_right(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_setl_click.assert_called_with(right=True)

    def test_arrow_right_map(self):
        """
        Ensure that the correct map panning occurs when pressing the right arrow key while no obscuring overlay is
        displayed.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.remove_warning_if_possible = MagicMock()
        pos_x, pos_y = self.game_state.map_pos = (5, 5)

        on_key_arrow_right(self.game_controller, self.game_state, False)
        self.assertTupleEqual((pos_x + 1, pos_y), self.game_state.map_pos)

        on_key_arrow_right(self.game_controller, self.game_state, True)
        self.assertTupleEqual((pos_x + 6, pos_y), self.game_state.map_pos)

        """
        Return cases to test

        Starting a game from the menu
        Pressing cancel on the load game screen
        Loading a game
        Going back from the Wiki
        Selecting an option in the Wiki
        Selecting an option on the main menu
        Returning to the menu after winning/being eliminated
        Choosing a construction
        Choosing a blessing
        Attacking a settlement - attacker killed
        Attacking a settlement - settlement taken, was besieged
        Besiege a settlement
        Leaving settlement click overlay
        Selecting an option on the pause overlay
        Ending a turn, with autosave
        """

    def test_shift(self):
        """
        Ensure that the correct overlay toggle occurs when the shift key is pressed.
        """
        self.game_state.game_started = True
        test_turn = self.game_state.turn = 99
        self.game_state.board.overlay.remove_warning_if_possible = MagicMock()
        self.game_state.board.overlay.toggle_standard = MagicMock()

        on_key_shift(self.game_state)
        self.game_state.board.overlay.remove_warning_if_possible.assert_called()
        self.game_state.board.overlay.toggle_standard.assert_called_with(test_turn)

    def test_c(self):
        """
        Ensure that the correct overlay toggle occurs when the C key is pressed.
        """
        self.game_state.game_started = True
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT
        self.game_state.board.overlay.toggle_construction = MagicMock()

        # We need to retrieve the improvements and unit plans ourselves first to compare them to the actual call.
        expected_improvements = get_available_improvements(self.TEST_PLAYER, self.TEST_SETTLEMENT)
        expected_unit_plans = get_available_unit_plans(self.TEST_PLAYER, self.TEST_SETTLEMENT.level)

        on_key_c(self.game_state)
        self.game_state.board.overlay.toggle_construction.assert_called_with(expected_improvements,
                                                                             PROJECTS,
                                                                             expected_unit_plans)

    def test_f_menu(self):
        """
        Ensure that the F key correctly toggles the additional faction details when in game setup on the menu.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.in_game_setup = True
        # Note that we set the setup option to be Fog of War.
        self.game_controller.menu.setup_option = SetupOption.FOG_OF_WAR

        # Since the setup option is not Player Faction, pressing F should do nothing.
        self.assertFalse(self.game_controller.menu.showing_faction_details)
        on_key_f(self.game_controller, self.game_state)
        self.assertFalse(self.game_controller.menu.showing_faction_details)

        # However, if we set the setup option to be Player Faction, pressing F should show additional faction details.
        self.game_controller.menu.setup_option = SetupOption.PLAYER_FACTION
        on_key_f(self.game_controller, self.game_state)
        self.assertTrue(self.game_controller.menu.showing_faction_details)

    def test_f_game(self):
        """
        Ensure that the F key correctly toggles the blessing overlay when viewing the standard overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.STANDARD]
        self.game_state.board.overlay.toggle_blessing = MagicMock()
        self.game_state.players.append(self.TEST_PLAYER)

        # Since the test player hasn't completed any blessings, every blessing is displayed.
        expected_blessings = list(BLESSINGS.values())
        expected_blessings.sort(key=lambda b: b.cost)
        on_key_f(self.game_controller, self.game_state)
        self.game_state.board.overlay.toggle_blessing.assert_called_with(expected_blessings)

    def test_d_deployment(self):
        """
        Ensure that the D key correctly toggles the deployment overlay when a unit in a settlement's garrison is being
        deployed.
        """
        self.game_state.game_started = True
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT
        self.game_state.board.overlay.toggle_deployment = MagicMock()

        # To begin with, nothing should happen, since the test settlement does not have any units in its garrison.
        self.assertFalse(self.game_state.board.deploying_army)
        on_key_d(self.game_state)
        self.assertFalse(self.game_state.board.deploying_army)
        self.game_state.board.overlay.toggle_deployment.assert_not_called()

        # However, if we add a unit to the garrison, the overlay should be toggled.
        self.TEST_SETTLEMENT.garrison.append(self.TEST_UNIT)
        on_key_d(self.game_state)
        self.assertTrue(self.game_state.board.deploying_army)
        self.game_state.board.overlay.toggle_deployment.assert_called()

    def test_d_disband(self):
        """
        Ensure that the D key correctly disbands the selected unit and credits the player.
        """
        self.game_state.game_started = True
        self.game_state.board.selected_unit = self.TEST_PLAYER.units[0]
        self.game_state.board.overlay.toggle_unit = MagicMock()

        self.assertEqual(self.PLAYER_WEALTH, self.TEST_PLAYER.wealth)
        self.assertTrue(self.TEST_PLAYER.units)
        on_key_d(self.game_state)
        # The player should now have their wealth increased by the value of the unit.
        self.assertEqual(self.PLAYER_WEALTH + UNIT_PLANS[0].cost, self.TEST_PLAYER.wealth)
        # Additionally, the player only had one unit, so they should now have no units.
        self.assertFalse(self.TEST_PLAYER.units)
        # Lastly, the unit should have been unselected and the overlay removed.
        self.assertIsNone(self.game_state.board.selected_unit)
        self.game_state.board.overlay.toggle_unit.assert_called_with(None)

    def test_tab(self):
        """
        Ensure that the correct iteration between settlements occurs when the TAB key is pressed.
        """
        self.game_state.game_started = True
        self.game_state.players = [self.TEST_PLAYER]
        self.game_state.board.overlay.remove_warning_if_possible = MagicMock()
        self.game_state.board.overlay.toggle_unit = MagicMock()
        self.game_state.board.overlay.toggle_settlement = MagicMock()
        self.game_state.board.overlay.update_settlement = MagicMock()

        # Set up a situation where the player has one of their units selected.
        self.game_state.board.overlay.showing = [OverlayType.UNIT]
        self.game_state.board.selected_unit = self.TEST_UNIT

        on_key_tab(self.game_state)
        # After the key is pressed, the selected unit and its overlay should be dismissed, and the player's first
        # settlement should be selected and centred.
        self.game_state.board.overlay.remove_warning_if_possible.assert_called()
        self.assertIsNone(self.game_state.board.selected_unit)
        self.game_state.board.overlay.toggle_unit.assert_called_with(None)
        self.assertEqual(self.TEST_SETTLEMENT, self.game_state.board.selected_settlement)
        self.game_state.board.overlay.toggle_settlement.assert_called_with(self.TEST_SETTLEMENT, self.TEST_PLAYER)
        self.assertTupleEqual((self.TEST_SETTLEMENT.location[0] - 12, self.TEST_SETTLEMENT.location[1] - 11),
                              self.game_state.map_pos)

        on_key_tab(self.game_state)
        # If we press the key again, the player's next settlement should be selected and centred.
        self.assertEqual(2, self.game_state.board.overlay.remove_warning_if_possible.call_count)
        self.assertEqual(self.TEST_SETTLEMENT_2, self.game_state.board.selected_settlement)
        self.game_state.board.overlay.update_settlement.assert_called_with(self.TEST_SETTLEMENT_2)
        self.assertTupleEqual((self.TEST_SETTLEMENT_2.location[0] - 12, self.TEST_SETTLEMENT_2.location[1] - 11),
                              self.game_state.map_pos)

    def test_space_menu_wiki(self):
        """
        Ensure that the Wiki returns to its menu when pressing the space key while viewing a Wiki option.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.in_wiki = True
        self.game_controller.menu.wiki_showing = WikiOption.VICTORIES
        on_key_space(self.game_controller, self.game_state)
        self.assertIsNone(self.game_controller.menu.wiki_showing)

    def test_space_menu_setup(self):
        """
        Ensure that the player is returned to the menu when pressing the space key while in game setup.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.in_game_setup = True
        on_key_space(self.game_controller, self.game_state)
        self.assertFalse(self.game_controller.menu.in_game_setup)

    def test_space_menu_load_failed(self):
        """
        Ensure that the load failed notification is removed when pressing the space key while it is displayed.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.loading_game = True
        self.game_controller.menu.load_failed = True
        on_key_space(self.game_controller, self.game_state)
        self.assertFalse(self.game_controller.menu.load_failed)

    def test_space_menu_loading(self):
        """
        Ensure that the player is returned to the menu when pressing the space key while viewing available game save
        files.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.loading_game = True
        on_key_space(self.game_controller, self.game_state)
        self.assertFalse(self.game_controller.menu.loading_game)

    def test_space_overlay(self):
        """
        Ensure that the space key correctly toggles in-game intrusive overlays.
        """
        def test_overlay(test_class: GameInputHandlerTest,
                         overlay_type: OverlayType,
                         fn_to_mock: str,
                         expected_args: typing.Optional[list]):
            """
            A helper function that sets the overlay, mocks its toggle function, and then expects a certain call to the
            mock.
            :param test_class: The GameInputHandlerTest class.
            :param overlay_type: The type of the overlay being added.
            :param fn_to_mock: The name of the overlay toggle function being mocked.
            :param expected_args: The arguments we expect the mock toggle function to be called with.
            """
            test_class.game_state.board.overlay.showing = [overlay_type]
            # Note that we have to use setattr() here so that we can make an assignment to a variable passed through as
            # a parameter.
            setattr(test_class.game_state.board.overlay, fn_to_mock, MagicMock())
            on_key_space(test_class.game_controller, test_class.game_state)
            # Since we are passed a string due to the setattr() requirement, we must also use getattr() here.
            if expected_args:
                getattr(test_class.game_state.board.overlay, fn_to_mock).assert_called_with(*expected_args)
            else:
                getattr(test_class.game_state.board.overlay, fn_to_mock).assert_called()

        self.game_state.game_started = True

        test_overlay(self, OverlayType.ELIMINATION, "toggle_elimination", [None])
        test_overlay(self, OverlayType.NIGHT, "toggle_night", [None])
        test_overlay(self, OverlayType.CLOSE_TO_VIC, "toggle_close_to_vic", [[]])
        test_overlay(self, OverlayType.BLESS_NOTIF, "toggle_blessing_notification", [None])
        test_overlay(self, OverlayType.CONSTR_NOTIF, "toggle_construction_notification", [None])
        test_overlay(self, OverlayType.LEVEL_NOTIF, "toggle_level_up_notification", [None])
        test_overlay(self, OverlayType.CONTROLS, "toggle_controls", None)
        test_overlay(self, OverlayType.INVESTIGATION, "toggle_investigation", [None])

    def test_space_units(self):
        """
        Ensure that the player can successfully iterate through their units when pressing the space key.
        """
        # Add another unit to the test player.
        self.TEST_PLAYER.units.append(self.TEST_UNIT_2)
        self.game_state.game_started = True
        self.game_state.board.overlay.remove_warning_if_possible = MagicMock()
        self.game_state.board.overlay.toggle_settlement = MagicMock()
        self.game_state.board.overlay.toggle_unit = MagicMock()
        self.game_state.board.overlay.update_unit = MagicMock()

        # Initialise the overlay to be showing a selected settlement.
        self.game_state.board.overlay.showing = [OverlayType.SETTLEMENT]
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT

        on_key_space(self.game_controller, self.game_state)
        self.game_state.board.overlay.remove_warning_if_possible.assert_called()
        # After the first press of the space key, the settlement should be deselected and its overlay removed.
        self.assertIsNone(self.game_state.board.selected_settlement)
        self.game_state.board.overlay.toggle_settlement.assert_called_with(None, self.TEST_PLAYER)
        # We also expect our first unit to be selected and centred, with its overlay displayed.
        self.assertEqual(self.TEST_UNIT, self.game_state.board.selected_unit)
        self.game_state.board.overlay.toggle_unit.assert_called_with(self.TEST_UNIT)
        self.assertTupleEqual((self.TEST_UNIT.location[0] - 12, self.TEST_UNIT.location[1] - 11),
                              self.game_state.map_pos)

        on_key_space(self.game_controller, self.game_state)
        self.assertEqual(2, self.game_state.board.overlay.remove_warning_if_possible.call_count)
        # After another press, we expect the second unit to be selected and centred.
        self.assertEqual(self.TEST_UNIT_2, self.game_state.board.selected_unit)
        self.game_state.board.overlay.update_unit.assert_called_with(self.TEST_UNIT_2)
        self.assertTupleEqual((self.TEST_UNIT_2.location[0] - 12, self.TEST_UNIT_2.location[1] - 11),
                              self.game_state.map_pos)

        on_key_space(self.game_controller, self.game_state)
        self.assertEqual(3, self.game_state.board.overlay.remove_warning_if_possible.call_count)
        # After the third press, we expect the selection to loop around and for the first unit to be selected again.
        self.assertEqual(self.TEST_UNIT, self.game_state.board.selected_unit)
        self.game_state.board.overlay.toggle_unit.assert_called_with(self.TEST_UNIT)
        self.assertTupleEqual((self.TEST_UNIT.location[0] - 12, self.TEST_UNIT.location[1] - 11),
                              self.game_state.map_pos)

    def test_s(self):
        """
        Ensure that the S key founds a new settlement when a settler unit is selected.
        """
        self.game_state.game_started = True
        self.game_state.board.selected_unit = \
            Unit(1, 1, (0, 0), False, UnitPlan(1, 1, 1, "Bob", None, 1, can_settle=True))
        self.game_state.board.handle_new_settlement = MagicMock()

        on_key_s(self.game_state)
        self.game_state.board.handle_new_settlement.assert_called_with(self.TEST_PLAYER)

    def test_n(self):
        """
        Ensure that the N key skips to the next song on the music player.
        """
        self.game_state.game_started = True
        self.game_controller.music_player.next_song = MagicMock()

        on_key_n(self.game_controller, self.game_state)
        self.game_controller.music_player.next_song.assert_called()

    def test_a(self):
        """
        Ensure that the A key automatically selects a construction for the selected settlement.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.SETTLEMENT]
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT

        self.assertIsNone(self.TEST_SETTLEMENT.current_work)
        on_key_a(self.game_state)
        self.assertIsNotNone(self.TEST_SETTLEMENT.current_work)

    def test_escape(self):
        """
        Ensure that the correct overlay changes occur when the escape key is pressed.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.toggle_pause = MagicMock()

        # If there are no overlays being shown, pressing escape should bring up the pause menu.
        self.game_state.board.overlay.showing = []
        on_key_escape(self.game_state)
        self.game_state.board.overlay.toggle_pause.assert_called()

        # Similarly, if only non-intrusive overlays are being shown, pressing escape should still bring up the pause
        # menu.
        self.game_state.board.overlay.showing = \
            [OverlayType.ATTACK, OverlayType.SETL_ATTACK, OverlayType.SIEGE_NOTIF, OverlayType.HEAL]
        on_key_escape(self.game_state)
        self.assertEqual(2, self.game_state.board.overlay.toggle_pause.call_count)

        # If the unit overlay is being displayed, pressing escape should deselect the unit and remove its overlay.
        self.game_state.board.overlay.showing = [OverlayType.UNIT]
        self.game_state.board.selected_unit = self.TEST_UNIT
        on_key_escape(self.game_state)
        self.assertFalse(self.game_state.board.overlay.showing)
        self.assertIsNone(self.game_state.board.selected_unit)

        # The same applies to settlements, with pressing escape when a settlement is selected leading to it being
        # deselected and its overlay dismissed.
        self.game_state.board.overlay.showing = [OverlayType.SETTLEMENT]
        self.game_state.board.selected_unit = self.TEST_SETTLEMENT
        on_key_escape(self.game_state)
        self.assertFalse(self.game_state.board.overlay.showing)
        self.assertIsNone(self.game_state.board.selected_settlement)

        # Lastly, if a particularly intrusive overlay such as the Tutorial or Deployment overlays are being displayed,
        # pressing escape should do nothing.
        self.game_state.board.overlay.showing = [OverlayType.TUTORIAL]
        on_key_escape(self.game_state)
        self.assertTrue(self.game_state.board.overlay.showing)

    def test_b_no_work(self):
        """
        Ensure that the B key has no effect when pressed for a settlement with no work.
        """
        self.game_state.game_started = True
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT
        self.game_state.board.overlay.toggle_construction_notification = MagicMock()

        self.assertIsNone(self.game_state.board.selected_settlement.current_work)
        on_key_b(self.game_state)
        self.game_state.board.overlay.toggle_construction_notification.assert_not_called()
        # We ensure that no change has occurred to the settlement by checking the improvements and garrison lists, as
        # well as any change in wealth.
        self.assertFalse(self.TEST_SETTLEMENT.improvements)
        self.assertFalse(self.TEST_SETTLEMENT.garrison)
        self.assertEqual(self.PLAYER_WEALTH, self.TEST_PLAYER.wealth)

    def test_b_fundamentalists(self):
        """
        Ensure that the B key has no effect when pressed by a player of the Fundamentalists faction.
        """
        self.game_state.game_started = True
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT_WITH_WORK
        self.game_state.board.overlay.toggle_construction_notification = MagicMock()
        self.TEST_PLAYER.faction = Faction.FUNDAMENTALISTS

        on_key_b(self.game_state)
        self.game_state.board.overlay.toggle_construction_notification.assert_not_called()
        # We ensure that no change has occurred to the settlement by checking the improvements and garrison lists, as
        # well as any change in wealth. We also make sure the original work is still assigned.
        self.assertFalse(self.TEST_SETTLEMENT_WITH_WORK.improvements)
        self.assertFalse(self.TEST_SETTLEMENT_WITH_WORK.garrison)
        self.assertIsNotNone(self.TEST_SETTLEMENT_WITH_WORK.current_work)
        self.assertEqual(self.PLAYER_WEALTH, self.TEST_PLAYER.wealth)

    def test_b_project(self):
        """
        Ensure that the B key has no effect when pressed for a settlement currently working on a Project.
        """
        test_settlement = Settlement("Projecton", (60, 60), [], [], [], current_work=Construction(PROJECTS[0]))
        self.game_state.game_started = True
        self.game_state.board.selected_settlement = test_settlement
        self.game_state.board.overlay.toggle_construction_notification = MagicMock()

        on_key_b(self.game_state)
        self.game_state.board.overlay.toggle_construction_notification.assert_not_called()
        # We ensure that no change has occurred to the settlement by checking the improvements and garrison lists, as
        # well as any change in wealth.
        self.assertFalse(test_settlement.improvements)
        self.assertFalse(test_settlement.garrison)
        self.assertEqual(self.PLAYER_WEALTH, self.TEST_PLAYER.wealth)

    def test_b_not_enough_wealth(self):
        """
        Ensure that the B key has no effect when pressed by a player without sufficient wealth to buyout the
        construction.
        """
        test_wealth = 1
        self.game_state.game_started = True
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT_WITH_WORK
        self.game_state.board.overlay.toggle_construction_notification = MagicMock()
        self.TEST_PLAYER.wealth = test_wealth

        on_key_b(self.game_state)
        self.game_state.board.overlay.toggle_construction_notification.assert_not_called()
        # We ensure that no change has occurred to the settlement by checking the improvements and garrison lists, as
        # well as any change in wealth. We also make sure the original work is still assigned.
        self.assertFalse(self.TEST_SETTLEMENT_WITH_WORK.improvements)
        self.assertFalse(self.TEST_SETTLEMENT_WITH_WORK.garrison)
        self.assertIsNotNone(self.TEST_SETTLEMENT_WITH_WORK.current_work)
        self.assertEqual(test_wealth, self.TEST_PLAYER.wealth)

    def test_b_buyout_success(self):
        """
        Ensure that the B key successfully buys out a settlement's current work when the appropriate criteria are met.
        """
        initial_work: Construction = self.TEST_SETTLEMENT_WITH_WORK.current_work
        self.game_state.game_started = True
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT_WITH_WORK
        self.game_state.board.overlay.toggle_construction_notification = MagicMock()

        on_key_b(self.game_state)
        # After the B key is pressed, the notification should have been toggled, the garrison populated, the original
        # work removed, and the player's wealth decreased appropriately.
        self.game_state.board.overlay.toggle_construction_notification.assert_called_with([
            CompletedConstruction(initial_work.construction, self.TEST_SETTLEMENT_WITH_WORK)
        ])
        self.assertFalse(self.TEST_SETTLEMENT_WITH_WORK.improvements)
        self.assertTrue(self.TEST_SETTLEMENT_WITH_WORK.garrison)
        self.assertIsNone(self.TEST_SETTLEMENT_WITH_WORK.current_work)
        self.assertEqual(self.PLAYER_WEALTH - initial_work.construction.cost, self.TEST_PLAYER.wealth)

    def test_m(self):
        """
        Ensure that the player can successfully iterate through their movable units when pressing the M key.
        """
        # Add a few more units to the test player, one standard, one with no stamina, and one that is besieging an enemy
        # settlement.
        self.TEST_PLAYER.units.extend([self.TEST_UNIT_2, self.TEST_UNIT_NO_STAMINA, self.TEST_UNIT_BESIEGING])
        self.game_state.game_started = True
        self.game_state.board.overlay.remove_warning_if_possible = MagicMock()
        self.game_state.board.overlay.toggle_settlement = MagicMock()
        self.game_state.board.overlay.toggle_unit = MagicMock()
        self.game_state.board.overlay.update_unit = MagicMock()

        # Initialise the overlay to be showing a selected settlement.
        self.game_state.board.overlay.showing = [OverlayType.SETTLEMENT]
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT

        on_key_m(self.game_state)
        self.game_state.board.overlay.remove_warning_if_possible.assert_called()
        # After the first press of the M key, the settlement should be deselected and its overlay removed.
        self.assertIsNone(self.game_state.board.selected_settlement)
        self.game_state.board.overlay.toggle_settlement.assert_called_with(None, self.TEST_PLAYER)
        # We also expect our first unit to be selected and centred, with its overlay displayed.
        self.assertEqual(self.TEST_UNIT, self.game_state.board.selected_unit)
        self.game_state.board.overlay.toggle_unit.assert_called_with(self.TEST_UNIT)
        self.assertTupleEqual((self.TEST_UNIT.location[0] - 12, self.TEST_UNIT.location[1] - 11),
                              self.game_state.map_pos)

        on_key_m(self.game_state)
        self.assertEqual(2, self.game_state.board.overlay.remove_warning_if_possible.call_count)
        # After another press, we expect the second unit to be selected and centred.
        self.assertEqual(self.TEST_UNIT_2, self.game_state.board.selected_unit)
        self.game_state.board.overlay.update_unit.assert_called_with(self.TEST_UNIT_2)
        self.assertTupleEqual((self.TEST_UNIT_2.location[0] - 12, self.TEST_UNIT_2.location[1] - 11),
                              self.game_state.map_pos)

        on_key_m(self.game_state)
        self.assertEqual(3, self.game_state.board.overlay.remove_warning_if_possible.call_count)
        # However, after the third press, we expect the first unit to be selected again. This is because the two
        # remaining units are not considered to be movable due to their lack of stamina and their besieging status,
        # respectively. As such, they are skipped.
        self.assertEqual(self.TEST_UNIT, self.game_state.board.selected_unit)
        self.game_state.board.overlay.toggle_unit.assert_called_with(self.TEST_UNIT)
        self.assertTupleEqual((self.TEST_UNIT.location[0] - 12, self.TEST_UNIT.location[1] - 11),
                              self.game_state.map_pos)

    def test_j(self):
        """
        Ensure that the player can successfully jump to idle settlements when pressing the J key.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.toggle_settlement = MagicMock()
        self.game_state.board.overlay.update_settlement = MagicMock()
        # Slightly change the order of the settlements to make this test's demonstration simpler.
        self.TEST_PLAYER.settlements = [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_WITH_WORK, self.TEST_SETTLEMENT_2]

        on_key_j(self.game_state)
        # Having not had any settlement selected beforehand, after the first press, the first settlement should be
        # selected and centred, with its overlay displayed.
        self.assertEqual(self.TEST_SETTLEMENT, self.game_state.board.selected_settlement)
        self.game_state.board.overlay.toggle_settlement.assert_called_with(self.TEST_SETTLEMENT, self.TEST_PLAYER)
        self.assertTupleEqual((self.TEST_SETTLEMENT.location[0] - 12, self.TEST_SETTLEMENT.location[1] - 11),
                              self.game_state.map_pos)

        on_key_j(self.game_state)
        # After the second press, note that, by order, our third settlement is now selected. This is because the second
        # settlement is skipped due to it not being idle.
        self.assertEqual(self.TEST_SETTLEMENT_2, self.game_state.board.selected_settlement)
        self.game_state.board.overlay.update_settlement.assert_called_with(self.TEST_SETTLEMENT_2)
        self.assertTupleEqual((self.TEST_SETTLEMENT_2.location[0] - 12, self.TEST_SETTLEMENT_2.location[1] - 11),
                              self.game_state.map_pos)

        # Lastly, if we select a settlement that isn't idle before pressing the key, rather than go to the next
        # settlement by order as the TAB key does, we expect the first idle settlement to be selected instead.
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT_WITH_WORK
        on_key_j(self.game_state)
        self.assertEqual(self.TEST_SETTLEMENT, self.game_state.board.selected_settlement)
        self.game_state.board.overlay.update_settlement.assert_called_with(self.TEST_SETTLEMENT)
        self.assertTupleEqual((self.TEST_SETTLEMENT.location[0] - 12, self.TEST_SETTLEMENT.location[1] - 11),
                              self.game_state.map_pos)


if __name__ == '__main__':
    unittest.main()
