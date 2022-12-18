import unittest
from unittest.mock import MagicMock, patch

from source.display.board import Board
from source.foundation.catalogue import Namer
from source.foundation.models import GameConfig, Faction, OverlayType
from source.game_management.game_controller import GameController
from source.game_management.game_input_handler import on_key_arrow_down, on_key_arrow_up
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
        pos_x, pos_y = self.game_state.map_pos

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
        pos_x, pos_y = self.game_state.map_pos

        on_key_arrow_up(self.game_controller, self.game_state, False)
        self.assertTupleEqual((pos_x, pos_y - 1), self.game_state.map_pos)

        on_key_arrow_up(self.game_controller, self.game_state, True)
        self.assertTupleEqual((pos_x, pos_y - 6), self.game_state.map_pos)


if __name__ == '__main__':
    unittest.main()
