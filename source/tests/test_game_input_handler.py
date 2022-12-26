import unittest
from unittest.mock import MagicMock, patch

from source.display.board import Board
from source.display.menu import SetupOption
from source.foundation.catalogue import Namer
from source.foundation.models import GameConfig, Faction, OverlayType, ConstructionMenu, Improvement, ImprovementType, \
    Effect, Project, ProjectType, UnitPlan
from source.game_management.game_controller import GameController
from source.game_management.game_input_handler import on_key_arrow_down, on_key_arrow_up, on_key_arrow_left, \
    on_key_arrow_right, on_key_shift, on_key_f
from source.game_management.game_state import GameState


class GameInputHandlerTest(unittest.TestCase):
    """
    The test class for game_input_handler.py.
    """

    @patch("source.game_management.game_controller.MusicPlayer")
    def setUp(self, _: MagicMock) -> None:
        """
        Set up the GameController and GameState objects to be used as parameters in the test functions. Also instantiate
        the Board object for the GameState. Note that we also mock out the MusicPlayer class that is used when
        constructing the GameController. This is because it will try to play music if not mocked.
        :param _: The unused MusicPlayer mock.
        """
        self.game_controller = GameController()
        self.game_state = GameState()
        self.game_state.board = Board(GameConfig(4, Faction.NOCTURNE, True, True, True), Namer())
        self.game_state.on_menu = False

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


if __name__ == '__main__':
    unittest.main()
