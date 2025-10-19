import unittest
from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict, Optional
from unittest.mock import MagicMock, patch

from source.display.board import Board
from source.display.menu import SetupOption, WikiOption, MainMenuOption
from source.foundation.catalogue import Namer, BLESSINGS, UNIT_PLANS, get_available_improvements, \
    get_available_unit_plans, PROJECTS, ACHIEVEMENTS, get_improvement, FACTION_COLOURS
from source.foundation.models import GameConfig, Faction, OverlayType, ConstructionMenu, Improvement, ImprovementType, \
    Effect, Project, ProjectType, UnitPlan, Player, Settlement, Unit, Construction, CompletedConstruction, \
    SettlementAttackType, PauseOption, Quad, Biome, DeployerUnitPlan, DeployerUnit, ResourceCollection, \
    StandardOverlayView, LobbyDetails, PlayerDetails, OngoingBlessing, MultiplayerStatus, SaveDetails
from source.game_management.game_controller import GameController
from source.game_management.game_input_handler import on_key_arrow_down, on_key_arrow_up, on_key_arrow_left, \
    on_key_arrow_right, on_key_shift, on_key_f, on_key_d, on_key_s, on_key_n, on_key_a, on_key_c, on_key_tab, \
    on_key_escape, on_key_m, on_key_j, on_key_space, on_key_b, on_key_return, on_key_x
from source.game_management.game_state import GameState
from source.networking.client import DispatcherKind, EventDispatcher
from source.networking.events import QuerySavesEvent, EventType, CreateEvent, InitEvent, LoadEvent, JoinEvent, \
    QueryEvent, LeaveEvent, SetConstructionEvent, UpdateAction, SetBlessingEvent, AttackSettlementEvent, \
    BesiegeSettlementEvent, SaveEvent, EndTurnEvent, UnreadyEvent, AutofillEvent, BuyoutConstructionEvent, \
    DisbandUnitEvent


class GameInputHandlerTest(unittest.TestCase):
    """
    The test class for game_input_handler.py.
    """
    PLAYER_WEALTH = 1000
    TEST_IDENTIFIER = 123
    TEST_MULTIPLAYER_CONFIG = GameConfig(2, Faction.AGRICULTURISTS, True, True, True, MultiplayerStatus.GLOBAL)
    TEST_EVENT_DISPATCHERS: Dict[DispatcherKind, EventDispatcher] = {DispatcherKind.GLOBAL: EventDispatcher()}

    @patch("source.game_management.game_controller.MusicPlayer")
    def setUp(self, _: MagicMock) -> None:
        """
        Set up the GameController and GameState objects to be used as parameters in the test functions. Also instantiate
        the Board object for the GameState and initialise test models. Note that we also mock out the MusicPlayer class
        that is used when constructing the GameController. This is because it will try to play music if not mocked.
        :param _: The unused MusicPlayer mock.
        """
        self.game_controller = GameController()
        self.game_state = GameState()
        self.game_state.event_dispatchers = self.TEST_EVENT_DISPATCHERS
        self.game_state.board = Board(GameConfig(4, Faction.NOCTURNE, True, True, True, MultiplayerStatus.DISABLED),
                                      Namer(), self.game_state.event_dispatchers)
        self.game_state.on_menu = False

        self.TEST_QUAD = Quad(Biome.FOREST, 0, 0, 0, 0, (40, 40))
        self.TEST_SETTLEMENT = Settlement("TestTown", (40, 40), [], [self.TEST_QUAD], ResourceCollection(), [])
        self.TEST_SETTLEMENT_2 = Settlement("TestCity", (50, 50), [], [], ResourceCollection(), [])
        self.TEST_SETTLEMENT_WITH_WORK = Settlement("Busyville", (60, 60), [], [], ResourceCollection(), [],
                                                    current_work=Construction(UNIT_PLANS[0]))
        self.TEST_UNIT = Unit(1, 1, (40, 40), True, UNIT_PLANS[0])
        self.TEST_UNIT_2 = Unit(2, 2, (50, 50), False, UNIT_PLANS[0])
        self.TEST_UNIT_NO_STAMINA = Unit(3, 0, (60, 60), False, UNIT_PLANS[0])
        self.TEST_UNIT_BESIEGING = Unit(4, 4, (70, 70), False, UNIT_PLANS[0], besieging=True)
        self.TEST_PLAYER = Player("Tester", Faction.NOCTURNE, 0, self.PLAYER_WEALTH,
                                  [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2, self.TEST_SETTLEMENT_WITH_WORK],
                                  [self.TEST_UNIT])
        self.TEST_PLAYER_2 = Player("Tester The Second", Faction.FUNDAMENTALISTS, 0)
        self.game_state.players = [self.TEST_PLAYER, self.TEST_PLAYER_2]
        self.game_state.player_idx = 0

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

    def test_arrow_down_unit(self):
        """
        Ensure that the correct method is called when pressing the down arrow key while viewing the unit overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.UNIT]
        self.game_state.board.overlay.navigate_unit = MagicMock()

        # If the deployer unit passenger view is not being displayed, the method should not be called.
        self.game_state.board.overlay.show_unit_passengers = False
        on_key_arrow_down(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_unit.assert_not_called()

        # However, if the passenger view is being displayed, the method should be called.
        self.game_state.board.overlay.show_unit_passengers = True
        on_key_arrow_down(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_unit.assert_called_with(down=True)

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
        self.game_state.board.overlay.navigate_standard.assert_called_with(up=True)

    def test_arrow_up_unit(self):
        """
        Ensure that the correct method is called when pressing the up arrow key while viewing the unit overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.UNIT]
        self.game_state.board.overlay.navigate_unit = MagicMock()

        # If the deployer unit passenger view is not being displayed, the method should not be called.
        self.game_state.board.overlay.show_unit_passengers = False
        on_key_arrow_up(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_unit.assert_not_called()

        # However, if the passenger view is being displayed, the method should be called.
        self.game_state.board.overlay.show_unit_passengers = True
        on_key_arrow_up(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_unit.assert_called_with(down=False)

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

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.get_saves")
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_arrow_left_menu_loading_multiplayer_game(self,
                                                      dispatch_mock: MagicMock,
                                                      get_saves_mock: MagicMock,
                                                      _: MagicMock):
        """
        Ensure that the correct behaviour occurs when pressing the left arrow key while loading a multiplayer game.
        """
        test_saves = ["abc", "def"]
        get_saves_mock.return_value = test_saves

        self.game_state.on_menu = True
        self.game_controller.menu.upnp_enabled = True
        self.game_controller.menu.loading_game = True
        self.game_controller.menu.navigate = MagicMock()

        # We start on the Local saves page in order to show the full sequence.
        self.game_controller.menu.loading_game_multiplayer_status = MultiplayerStatus.LOCAL

        on_key_arrow_left(self.game_controller, self.game_state, False)

        self.game_controller.menu.navigate.assert_called_with(left=True)
        # On the first key press, we expect an event to have been dispatched to the game server to get all global saves.
        expected_event: QuerySavesEvent = QuerySavesEvent(EventType.QUERY_SAVES, self.TEST_IDENTIFIER)
        dispatch_mock.assert_called_with(expected_event, self.TEST_EVENT_DISPATCHERS, MultiplayerStatus.GLOBAL)

        # Ordinarily this would be changed by the event listener, but we have to help the menu along here by simulating
        # the multiplayer status changing.
        self.game_controller.menu.loading_game_multiplayer_status = MultiplayerStatus.GLOBAL

        on_key_arrow_left(self.game_controller, self.game_state, False)

        # On the second key press, since we've now toggled to local single-player saves, the saves mock should have been
        # called.
        self.game_controller.menu.navigate.assert_called_with(left=True)
        self.assertListEqual(test_saves, self.game_controller.menu.saves)

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_arrow_left_menu_viewing_local_lobbies(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the correct event is dispatched when pressing the left arrow key while viewing local multiplayer
        lobbies.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.upnp_enabled = True
        self.game_controller.menu.viewing_lobbies = True
        self.game_controller.menu.viewing_local_lobbies = True
        self.game_controller.menu.navigate = MagicMock()

        on_key_arrow_left(self.game_controller, self.game_state, False)

        self.game_controller.menu.navigate.assert_called_with(left=True)
        # We expect an event to have been dispatched to the game server to get all global lobbies.
        expected_event: QueryEvent = QueryEvent(EventType.QUERY, self.TEST_IDENTIFIER)
        dispatch_mock.assert_called_with(expected_event, self.TEST_EVENT_DISPATCHERS, MultiplayerStatus.GLOBAL)

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
        # Technically the construction boundaries could never be this with only one available improvement, but we set
        # them to this in order to verify that they are reset when returning to the improvements menu.
        self.game_state.board.overlay.construction_boundaries = 1, 6

        # Now that an available construction has been assigned, the improvements menu should be viewable.
        on_key_arrow_left(self.game_controller, self.game_state, False)
        self.assertEqual(ConstructionMenu.IMPROVEMENTS, self.game_state.board.overlay.current_construction_menu)
        self.assertEqual(test_improvement, self.game_state.board.overlay.selected_construction)
        self.assertTupleEqual((0, 5), self.game_state.board.overlay.construction_boundaries)

        self.game_state.board.overlay.current_construction_menu = ConstructionMenu.UNITS
        self.game_state.board.overlay.available_projects = [test_project]

        # From the units menu, pressing left should bring us to the projects menu.
        on_key_arrow_left(self.game_controller, self.game_state, False)
        self.assertEqual(ConstructionMenu.PROJECTS, self.game_state.board.overlay.current_construction_menu)
        self.assertEqual(test_project, self.game_state.board.overlay.selected_construction)

    def test_arrow_left_standard(self):
        """
        Ensure that the correct method is called when pressing the left arrow key while viewing the standard overlay.
        """
        self.game_state.game_started = True

        # To begin with, we simulate that the player is selecting a blessing to undergo. As such, pressing left should
        # have no effect despite the user currently technically viewing the standard overlay (beneath the blessing
        # overlay).
        self.game_state.board.overlay.showing = [OverlayType.STANDARD, OverlayType.BLESSING]
        self.game_state.board.overlay.navigate_standard = MagicMock()
        on_key_arrow_left(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_standard.assert_not_called()

        # Now with the user only viewing the standard overlay, we expect the navigation method to be called with the
        # correct argument.
        self.game_state.board.overlay.showing = [OverlayType.STANDARD]
        self.game_state.board.overlay.navigate_standard = MagicMock()
        on_key_arrow_left(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_standard.assert_called_with(left=True)

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

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_arrow_right_menu_loading_game(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the correct method is called and the correct event is dispatched when pressing the right arrow key
        while on the menu and loading a game.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.loading_game = True
        self.game_controller.menu.upnp_enabled = True
        self.game_controller.menu.has_local_dispatcher = False
        self.game_controller.menu.navigate = MagicMock()

        on_key_arrow_right(self.game_controller, self.game_state, False)

        self.game_controller.menu.navigate.assert_called_with(right=True)
        # On the first key press, we expect an event to have been dispatched to load global saves.
        expected_event: QuerySavesEvent = QuerySavesEvent(EventType.QUERY_SAVES, self.TEST_IDENTIFIER)
        dispatch_mock.assert_called_with(expected_event, self.TEST_EVENT_DISPATCHERS, MultiplayerStatus.GLOBAL)

        # To simulate real behaviour, we manually change the multiplayer status to global for the following key presses.
        self.game_controller.menu.loading_game_multiplayer_status = MultiplayerStatus.GLOBAL
        self.game_controller.menu.navigate.reset_mock()
        dispatch_mock.reset_mock()

        on_key_arrow_right(self.game_controller, self.game_state, False)

        self.game_controller.menu.navigate.assert_called_with(right=True)
        # Since there is no local dispatcher, we expect no event to have been dispatched to query local multiplayer
        # saves.
        dispatch_mock.assert_not_called()

        # However, with a local dispatcher, we expect an event to be dispatched.
        self.game_controller.menu.has_local_dispatcher = True
        self.game_controller.menu.navigate.reset_mock()
        dispatch_mock.reset_mock()

        on_key_arrow_right(self.game_controller, self.game_state, False)

        self.game_controller.menu.navigate.assert_called_with(right=True)
        # We now expect an event to have been dispatched to load local multiplayer saves.
        dispatch_mock.assert_called_with(expected_event, self.TEST_EVENT_DISPATCHERS, MultiplayerStatus.LOCAL)

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_arrow_right_menu_viewing_lobbies(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the correct event is dispatched when pressing the right arrow key while viewing global multiplayer
        lobbies.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.viewing_lobbies = True
        self.game_controller.menu.has_local_dispatcher = False
        self.game_controller.menu.navigate = MagicMock()

        on_key_arrow_right(self.game_controller, self.game_state, False)

        self.game_controller.menu.navigate.assert_called_with(right=True)
        # On the first key press, we expect no event to have been dispatched to view local lobbies because there is no
        # local dispatcher.
        dispatch_mock.assert_not_called()

        # However, with a local dispatcher we expect an event to be dispatched.
        self.game_controller.menu.has_local_dispatcher = True

        on_key_arrow_right(self.game_controller, self.game_state, False)

        self.game_controller.menu.navigate.assert_called_with(right=True)
        # We now expect an event to have been dispatched to query for local multiplayer lobbies.
        expected_event: QueryEvent = QueryEvent(EventType.QUERY, self.TEST_IDENTIFIER)
        dispatch_mock.assert_called_with(expected_event, self.TEST_EVENT_DISPATCHERS, MultiplayerStatus.LOCAL)

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

    def test_arrow_right_standard(self):
        """
        Ensure that the correct method is called when pressing the right arrow key while viewing the standard overlay.
        """
        self.game_state.game_started = True

        # To begin with, we simulate that the player is selecting a blessing to undergo. As such, pressing right should
        # have no effect despite the user currently technically viewing the standard overlay (beneath the blessing
        # overlay).
        self.game_state.board.overlay.showing = [OverlayType.STANDARD, OverlayType.BLESSING]
        self.game_state.board.overlay.navigate_standard = MagicMock()
        on_key_arrow_right(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_standard.assert_not_called()

        # Now with the user only viewing the standard overlay, we expect the navigation method to be called with the
        # correct argument.
        self.game_state.board.overlay.showing = [OverlayType.STANDARD]
        self.game_state.board.overlay.navigate_standard = MagicMock()
        on_key_arrow_right(self.game_controller, self.game_state, False)
        self.game_state.board.overlay.navigate_standard.assert_called_with(right=True)

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

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_return_create_multiplayer_lobby(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that when pressing the return key while in game setup and selecting the Start Game button with a game
        configuration where multiplayer is enabled, the correct event is dispatched to the game server.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.in_game_setup = True
        self.game_controller.menu.setup_option = SetupOption.START_GAME
        self.game_controller.menu.multiplayer_status = MultiplayerStatus.GLOBAL

        # This test suite initialises a game state object before each test, so these should be populated.
        self.assertIsNotNone(self.game_state.board)
        self.assertTrue(self.game_state.players)

        on_key_return(self.game_controller, self.game_state)

        # We now expect the game state to be reset, and a CreateEvent to have been sent to the game server.
        self.assertIsNone(self.game_state.board)
        self.assertFalse(self.game_state.players)
        expected_event = CreateEvent(EventType.CREATE, self.TEST_IDENTIFIER, self.TEST_MULTIPLAYER_CONFIG)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_return_start_multiplayer_game(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the correct behaviour occurs when pressing the return key while in a multiplayer lobby.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.setup_option = SetupOption.START_GAME
        self.game_controller.menu.multiplayer_status = MultiplayerStatus.GLOBAL
        lobby_name = "Cool Lobby"

        self.game_controller.menu.multiplayer_lobby = \
            LobbyDetails(lobby_name, [PlayerDetails("Bob", Faction.AGRICULTURISTS, 123)],
                         self.TEST_MULTIPLAYER_CONFIG, None)
        # Because there is only one player currently in the lobby, we expect no event to have been dispatched.
        on_key_return(self.game_controller, self.game_state)
        dispatch_mock.assert_not_called()

        self.game_controller.menu.multiplayer_lobby.current_players.append(PlayerDetails("Jack", Faction.NOCTURNE, 345))
        # Now with a second player in the lobby, we expect the appropriate event to have been dispatched with this
        # lobby's name.
        on_key_return(self.game_controller, self.game_state)
        expected_event = InitEvent(EventType.INIT, self.TEST_IDENTIFIER, lobby_name)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)

    @patch("source.game_management.game_input_handler.save_stats_achievements")
    @patch("random.seed")
    @patch("pyxel.mouse")
    def test_return_start_game(self, mouse_mock: MagicMock, random_mock: MagicMock,
                               save_stats_achievements_mock: MagicMock):
        """
        Ensure that when pressing the return key while in game setup and selecting the Start Game button, the correct
        game preparation state modification occurs.
        :param mouse_mock: The mock representation of pyxel.mouse().
        :param random_mock: The mock representation of random.seed().
        :param save_stats_achievements_mock: The mock implementation of the save_stats_achievements() function.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.in_game_setup = True
        self.game_controller.menu.setup_option = SetupOption.START_GAME
        self.game_controller.namer.reset = MagicMock()
        self.game_controller.music_player.stop_menu_music = MagicMock()
        self.game_controller.music_player.play_game_music = MagicMock()

        # In this test suite, the game state is initialised before each test. We reset it here so that we can properly
        # verify the functionality.
        self.game_state.players = []
        self.game_state.board = None

        self.assertFalse(self.game_state.game_started)
        self.assertIsNone(self.game_controller.move_maker.board_ref)
        self.assertFalse(hasattr(self.game_controller, "last_turn_time"))
        self.assertFalse(self.game_state.located_player_idx)

        on_key_return(self.game_controller, self.game_state)

        mouse_mock.assert_called_with(visible=True)
        self.assertTrue(hasattr(self.game_controller, "last_turn_time"))
        self.assertEqual(0, self.game_state.player_idx)
        self.assertTrue(self.game_state.located_player_idx)
        self.assertTrue(self.game_state.game_started)
        self.assertEqual(1, self.game_state.turn)
        random_mock.assert_called()
        # We use assertAlmostEqual() here because the number of turns until night can be between 10 and 20. We don't
        # really care what the value is, just that it's within that range.
        self.assertAlmostEqual(15, self.game_state.until_night, delta=5)
        self.assertFalse(self.game_state.nighttime_left)
        self.assertFalse(self.game_state.on_menu)
        # Since we're starting a new game, the faction statistic should be updated with the first faction, which is the
        # Agriculturists. We expect it to be the first faction because we haven't updated the index.
        save_stats_achievements_mock.assert_called_with(self.game_state, faction_to_add=Faction.AGRICULTURISTS)
        # The players and board should now be initialised.
        self.assertTrue(self.game_state.players)
        self.assertIsNotNone(self.game_state.board)
        self.assertIsNotNone(self.game_controller.move_maker.board_ref)
        # The tutorial overlay should now be displayed.
        self.assertTrue(self.game_state.board.overlay.is_tutorial())
        self.game_controller.namer.reset.assert_called()
        # The AI players should now each have a settlement.
        self.assertTrue(all(player.settlements for player in self.game_state.players if player.ai_playstyle))
        # The total settlement count should also have been set in the overlay - incremented by 1 because the player will
        # not have founded their settlement yet.
        self.assertEqual(2, self.game_state.board.overlay.total_settlement_count)
        self.game_controller.music_player.stop_menu_music.assert_called()
        self.game_controller.music_player.play_game_music.assert_called()

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_return_load_multiplayer_game(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that when pressing the return key while on the load multiplayer game screen with a save selected, the
        correct load event is dispatched to the game server.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.loading_game = True
        self.game_controller.menu.loading_game_multiplayer_status = MultiplayerStatus.GLOBAL
        # A current save game with further details like turn and player count should be formatted into the current file
        # name format. Note that we have to specify the time zone to guarantee consistent epoch conversion.
        autosave: SaveDetails = SaveDetails(datetime(2024, 6, 22, 20, 15, 0, tzinfo=timezone.utc), auto=True,
                                            turn=99, player_count=2, faction=None, multiplayer=True)
        autosave_file_name: str = "autosave_1719087300_99_2_M.json"
        # A legacy save game with no details beyond the time should be formatted into the legacy format.
        save: SaveDetails = SaveDetails(datetime(2024, 6, 22, 20, 0, 0), False)
        save_file_name: str = "save-2024-06-22T20.00.00.json"
        self.game_controller.menu.saves = [autosave, save]

        self.game_controller.menu.save_idx = 0
        on_key_return(self.game_controller, self.game_state)
        expected_event = LoadEvent(EventType.LOAD, self.TEST_IDENTIFIER, autosave_file_name)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)

        self.game_controller.menu.save_idx = 1
        on_key_return(self.game_controller, self.game_state)
        expected_event = LoadEvent(EventType.LOAD, self.TEST_IDENTIFIER, save_file_name)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)

    @patch("source.game_management.game_input_handler.load_game")
    def test_return_load_game(self, load_mock: MagicMock):
        """
        Ensure that when pressing the return key while on the load game screen with a save selected, the save is loaded.
        :param load_mock: The mock implementation of the load_game() function.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.loading_game = True
        self.game_controller.menu.save_idx = 9
        on_key_return(self.game_controller, self.game_state)
        load_mock.assert_called_with(self.game_state, self.game_controller)

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_return_join_multiplayer_game(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the correct behaviour occurs when pressing the return key while joining a multiplayer game.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.joining_game = True
        self.game_controller.namer.reset = MagicMock()
        lobby_name = "Uno"
        available_faction = Faction.NOCTURNE
        # Obviously these lobbies and factions are not realistic since the lobby has no players and the faction colour
        # is wrong, but they're enough for our testing purposes.
        self.game_controller.menu.multiplayer_lobbies = \
            [LobbyDetails(lobby_name, [], self.TEST_MULTIPLAYER_CONFIG, None)]
        self.game_controller.menu.available_multiplayer_factions = [(available_faction, 0)]

        self.game_controller.menu.showing_faction_details = True
        # Because the faction details are currently being displayed, we don't expect anything to happen when the return
        # key is pressed.
        on_key_return(self.game_controller, self.game_state)
        dispatch_mock.assert_not_called()
        self.game_controller.namer.reset.assert_not_called()

        self.game_controller.menu.showing_faction_details = False
        # Now with the faction details not being displayed, we expect the correct event to be dispatched, and the namer
        # to have been reset.
        on_key_return(self.game_controller, self.game_state)
        expected_event = JoinEvent(EventType.JOIN, self.TEST_IDENTIFIER, lobby_name, available_faction)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)
        self.game_controller.namer.reset.assert_called()

    def test_return_joining_multiplayer_lobby(self):
        """
        Ensure that the correct behaviour occurs when pressing the return key while viewing multiplayer lobbies for
        games that have not yet started.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.viewing_lobbies = True

        lobby_players = [PlayerDetails("Alvin", Faction.AGRICULTURISTS, 123),
                         PlayerDetails("Brett", Faction.NOCTURNE, 456)]
        self.game_controller.menu.multiplayer_lobbies = \
            [LobbyDetails("El Lobbo", lobby_players, self.TEST_MULTIPLAYER_CONFIG, None)]
        # Because the test multiplayer game config we're using has two players, and there are already two human players
        # in the lobby, we expect nothing to happen when the return key is pressed.
        on_key_return(self.game_controller, self.game_state)
        self.assertFalse(self.game_controller.menu.joining_game)

        # However, if we make the second player an AI, we expect the appropriate factions to be available. That is, all
        # factions but the one used by the human player.
        lobby_players[1].id = None
        on_key_return(self.game_controller, self.game_state)
        expected_factions = deepcopy(FACTION_COLOURS)
        expected_factions.pop(lobby_players[0].faction)
        self.assertListEqual(list(expected_factions.items()), self.game_controller.menu.available_multiplayer_factions)
        self.assertTrue(self.game_controller.menu.joining_game)
        self.assertEqual(self.TEST_MULTIPLAYER_CONFIG.multiplayer, self.game_controller.menu.multiplayer_status)

    def test_return_joining_multiplayer_lobby_in_progress(self):
        """
        Ensure that the correct behaviour occurs when pressing the return key while viewing multiplayer lobbies for
        games that have started.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.viewing_lobbies = True

        lobby_players = [PlayerDetails("Alvin", Faction.AGRICULTURISTS, 123),
                         PlayerDetails("Brett", Faction.NOCTURNE, 456)]
        self.game_controller.menu.multiplayer_lobbies = \
            [LobbyDetails("El Lobbo", lobby_players, self.TEST_MULTIPLAYER_CONFIG, current_turn=13)]
        # Because the test multiplayer game config we're using has two players, and there are already two human players
        # in the lobby, we expect nothing to happen when the return key is pressed.
        on_key_return(self.game_controller, self.game_state)
        self.assertFalse(self.game_controller.menu.joining_game)

        # However, if we make the second player an AI, we expect the appropriate faction to be available. That is, the
        # one faction used by the AI player, since the game is ongoing.
        lobby_players[1].id = None
        on_key_return(self.game_controller, self.game_state)
        self.assertListEqual([(lobby_players[1].faction, FACTION_COLOURS[lobby_players[1].faction])],
                             self.game_controller.menu.available_multiplayer_factions)
        self.assertTrue(self.game_controller.menu.joining_game)

    def test_return_exit_wiki(self):
        """
        Ensure that when pressing the return key while in the wiki menu with the back button selected, the player is
        returned to the main menu.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.in_wiki = True
        self.game_controller.menu.wiki_option = WikiOption.BACK
        on_key_return(self.game_controller, self.game_state)
        self.assertFalse(self.game_controller.menu.in_wiki)

    def test_return_select_wiki_option(self):
        """
        Ensure that when pressing the return key while in the wiki menu with a wiki option selected, the player is taken
        to the wiki page for the selected option.
        """
        wiki_option = WikiOption.VICTORIES

        self.game_state.on_menu = True
        self.game_controller.menu.in_wiki = True
        self.game_controller.menu.wiki_option = wiki_option

        on_key_return(self.game_controller, self.game_state)

        self.assertEqual(wiki_option, self.game_controller.menu.wiki_showing)

    def test_return_select_main_menu_option_new_game(self):
        """
        Ensure that the game setup page is presented to the player after pressing the return key on the main menu with
        the New Game option selected.
        """
        self.game_state.on_menu = True
        self.assertFalse(self.game_controller.menu.in_game_setup)
        self.game_controller.menu.main_menu_option = MainMenuOption.NEW_GAME
        on_key_return(self.game_controller, self.game_state)
        self.assertTrue(self.game_controller.menu.in_game_setup)

    @patch("source.game_management.game_input_handler.get_saves")
    def test_return_select_main_menu_option_load_game(self, get_saves_mock: MagicMock):
        """
        Ensure that the load game page is presented to the player after pressing the return key on the main menu with
        the Load Game option selected.
        :param get_saves_mock: The mock implementation of the get_saves() function.
        """
        test_saves = ["abc", "def"]
        get_saves_mock.return_value = test_saves

        self.game_state.on_menu = True
        self.assertFalse(self.game_controller.menu.loading_game)
        self.game_controller.menu.main_menu_option = MainMenuOption.LOAD_GAME
        on_key_return(self.game_controller, self.game_state)
        self.assertTrue(self.game_controller.menu.loading_game)
        self.assertEqual(test_saves, self.game_controller.menu.saves)

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_return_select_main_menu_option_join_game(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the expected event is dispatched to the game server after pressing the return key on the main menu
        with the Join Game option selected.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.upnp_enabled = True
        self.game_controller.menu.main_menu_option = MainMenuOption.JOIN_GAME
        on_key_return(self.game_controller, self.game_state)
        expected_event = QueryEvent(EventType.QUERY, self.TEST_IDENTIFIER)
        dispatch_mock.assert_called_with(expected_event, self.TEST_EVENT_DISPATCHERS, MultiplayerStatus.GLOBAL)

    def test_return_select_main_menu_option_statistics(self):
        """
        Ensure that the statistics page is presented to the player after pressing the return key on the main menu with
        the Statistics option selected.
        """
        self.game_state.on_menu = True
        self.assertFalse(self.game_controller.menu.viewing_stats)
        self.assertIsNone(self.game_controller.menu.player_stats)
        self.game_controller.menu.main_menu_option = MainMenuOption.STATISTICS
        on_key_return(self.game_controller, self.game_state)
        self.assertTrue(self.game_controller.menu.viewing_stats)
        self.assertIsNotNone(self.game_controller.menu.player_stats)

    def test_return_select_main_menu_option_achievements(self):
        """
        Ensure that the achievements page is presented to the player after pressing the return key on the main menu with
        the Achievements option selected.
        """
        self.game_state.on_menu = True
        self.assertFalse(self.game_controller.menu.viewing_achievements)
        self.assertIsNone(self.game_controller.menu.player_stats)
        self.game_controller.menu.main_menu_option = MainMenuOption.ACHIEVEMENTS
        on_key_return(self.game_controller, self.game_state)
        self.assertTrue(self.game_controller.menu.viewing_achievements)
        self.assertIsNotNone(self.game_controller.menu.player_stats)

    def test_return_select_main_menu_option_wiki(self):
        """
        Ensure that the wiki menu is presented to the player after pressing the return key on the main menu with the
        Wiki option selected.
        """
        self.game_state.on_menu = True
        self.assertFalse(self.game_controller.menu.in_wiki)
        self.game_controller.menu.main_menu_option = MainMenuOption.WIKI
        on_key_return(self.game_controller, self.game_state)
        self.assertTrue(self.game_controller.menu.in_wiki)

    @patch("pyxel.quit")
    def test_return_select_main_menu_option_exit(self, quit_mock: MagicMock):
        """
        Ensure that the game is exited after pressing the return key on the main menu with the Exit option selected.
        :param quit_mock: The mock implementation of pyxel.quit().
        """
        self.game_state.on_menu = True
        self.game_controller.menu.main_menu_option = MainMenuOption.EXIT
        on_key_return(self.game_controller, self.game_state)
        quit_mock.assert_called()

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_return_back_to_menu_desync_multiplayer(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the player is brought back to the main menu when pressing the return key after a desync has occurred
        in a multiplayer game.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.DESYNC]
        self.game_state.board.game_config = self.TEST_MULTIPLAYER_CONFIG
        lobby_name = "Large Lobby"
        # Obviously this lobby is not realistic since it has no players, but it's enough for our testing purposes.
        self.game_controller.menu.multiplayer_lobby = LobbyDetails(lobby_name, [], self.TEST_MULTIPLAYER_CONFIG, 99)
        self.game_controller.namer.reset = MagicMock()
        self.game_controller.music_player.stop_game_music = MagicMock()
        self.game_controller.music_player.play_menu_music = MagicMock()

        self.assertFalse(self.game_state.on_menu)

        on_key_return(self.game_controller, self.game_state)

        # We expect an event with the appropriate attributes to have been dispatched to the game server. Note that we
        # expect this in all cases, since a desync can only occur in multiplayer games.
        expected_event = JoinEvent(EventType.JOIN, self.TEST_IDENTIFIER, lobby_name, self.TEST_PLAYER.faction)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)

        self.assertFalse(self.game_state.game_started)
        self.assertTrue(self.game_state.on_menu)
        self.assertIsNone(self.game_state.board)
        self.assertFalse(self.game_state.players)
        self.game_controller.namer.reset.assert_called()
        self.game_controller.music_player.stop_game_music.assert_called()
        self.game_controller.music_player.play_menu_music.assert_called()

    def test_return_back_to_menu_victory(self):
        """
        Ensure that when pressing the return key after winning a game, the player is brought back to the main menu.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.VICTORY]
        self.game_controller.music_player.stop_game_music = MagicMock()
        self.game_controller.music_player.play_menu_music = MagicMock()

        self.assertFalse(self.game_state.on_menu)

        on_key_return(self.game_controller, self.game_state)

        self.assertFalse(self.game_state.game_started)
        self.assertTrue(self.game_state.on_menu)
        self.assertIsNone(self.game_state.board)
        self.assertFalse(self.game_state.players)
        self.assertFalse(self.game_controller.menu.loading_game)
        self.assertFalse(self.game_controller.menu.loading_game_multiplayer_status)
        self.assertFalse(self.game_controller.menu.in_game_setup)
        self.assertIsNone(self.game_controller.menu.multiplayer_lobby)
        self.assertFalse(self.game_controller.menu.joining_game)
        self.assertFalse(self.game_controller.menu.viewing_lobbies)
        self.assertFalse(self.game_controller.menu.viewing_local_lobbies)
        self.assertFalse(self.game_controller.menu.faction_idx)
        self.assertEqual(MainMenuOption.NEW_GAME, self.game_controller.menu.main_menu_option)
        self.game_controller.music_player.stop_game_music.assert_called()
        self.game_controller.music_player.play_menu_music.assert_called()

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_return_back_to_menu_victory_multiplayer(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that when pressing the return key after winning a multiplayer game, the player is brought back to the
        main menu.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.VICTORY]
        self.game_state.board.game_config = self.TEST_MULTIPLAYER_CONFIG
        lobby_name = "Large Lobby"
        # Obviously this lobby is not realistic since it has no players, but it's enough for our testing purposes.
        self.game_controller.menu.multiplayer_lobby = LobbyDetails(lobby_name, [], self.TEST_MULTIPLAYER_CONFIG, 99)
        self.game_controller.music_player.stop_game_music = MagicMock()
        self.game_controller.music_player.play_menu_music = MagicMock()

        self.assertFalse(self.game_state.on_menu)

        on_key_return(self.game_controller, self.game_state)

        # Since this is a multiplayer game, we also expect an event with the appropriate attributes to have been
        # dispatched to the game server.
        expected_event = LeaveEvent(EventType.LEAVE, self.TEST_IDENTIFIER, lobby_name)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)

        self.assertFalse(self.game_state.game_started)
        self.assertTrue(self.game_state.on_menu)
        self.assertIsNone(self.game_state.board)
        self.assertFalse(self.game_state.players)
        self.assertFalse(self.game_controller.menu.loading_game)
        self.assertFalse(self.game_controller.menu.loading_game_multiplayer_status)
        self.assertFalse(self.game_controller.menu.in_game_setup)
        self.assertIsNone(self.game_controller.menu.multiplayer_lobby)
        self.assertFalse(self.game_controller.menu.joining_game)
        self.assertFalse(self.game_controller.menu.viewing_lobbies)
        self.assertFalse(self.game_controller.menu.viewing_local_lobbies)
        self.assertFalse(self.game_controller.menu.faction_idx)
        self.assertEqual(MainMenuOption.NEW_GAME, self.game_controller.menu.main_menu_option)
        self.game_controller.music_player.stop_game_music.assert_called()
        self.game_controller.music_player.play_menu_music.assert_called()

    def test_return_back_to_menu_eliminated(self):
        """
        Ensure that when pressing the return key after being eliminated from a game, the player is brought back to the
        main menu.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.ELIMINATION]
        self.game_state.players[0].eliminated = True
        self.game_controller.music_player.stop_game_music = MagicMock()
        self.game_controller.music_player.play_menu_music = MagicMock()

        self.assertFalse(self.game_state.on_menu)

        on_key_return(self.game_controller, self.game_state)

        self.assertFalse(self.game_state.game_started)
        self.assertTrue(self.game_state.on_menu)
        self.assertIsNone(self.game_state.board)
        self.assertFalse(self.game_state.players)
        self.assertFalse(self.game_controller.menu.loading_game)
        self.assertFalse(self.game_controller.menu.loading_game_multiplayer_status)
        self.assertFalse(self.game_controller.menu.in_game_setup)
        self.assertIsNone(self.game_controller.menu.multiplayer_lobby)
        self.assertFalse(self.game_controller.menu.joining_game)
        self.assertFalse(self.game_controller.menu.viewing_lobbies)
        self.assertFalse(self.game_controller.menu.viewing_local_lobbies)
        self.assertFalse(self.game_controller.menu.faction_idx)
        self.assertEqual(MainMenuOption.NEW_GAME, self.game_controller.menu.main_menu_option)
        self.game_controller.music_player.stop_game_music.assert_called()
        self.game_controller.music_player.play_menu_music.assert_called()

    def test_return_select_construction(self):
        """
        Ensure that pressing the return key when selecting a construction for a settlement has the expected effect,
        based on whether the player has the required resources for the construction.
        """
        self.game_state.board.overlay.toggle_construction = MagicMock()
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.CONSTRUCTION]
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT

        # To begin with, we attempt to select a construction that requires resources that the player does not have.
        # Melting Pot suits for this purpose, as it requires 5 magma, and the player has no resources to start with.
        self.game_state.board.overlay.selected_construction = get_improvement("Melting Pot")
        on_key_return(self.game_controller, self.game_state)
        # The construction should not have been begun, and the overlay should still be displayed.
        self.assertIsNone(self.TEST_SETTLEMENT.current_work)
        self.game_state.board.overlay.toggle_construction.assert_not_called()

        # However, if we give the player the required resources, they should be able to select the same construction.
        self.game_state.players[0].resources = ResourceCollection(magma=5)
        on_key_return(self.game_controller, self.game_state)
        # The player should also have had their resources deducted.
        self.assertFalse(self.game_state.players[0].resources.magma)
        self.assertEqual(get_improvement("Melting Pot"), self.TEST_SETTLEMENT.current_work.construction)
        self.game_state.board.overlay.toggle_construction.assert_called_with([], [], [])

        # Lastly, we choose City Market because it's a basic improvement that does not require resources to construct.
        self.game_state.board.overlay.selected_construction = get_improvement("City Market")
        on_key_return(self.game_controller, self.game_state)
        self.assertEqual(get_improvement("City Market"), self.TEST_SETTLEMENT.current_work.construction)
        self.game_state.board.overlay.toggle_construction.assert_called_with([], [], [])

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_return_select_construction_multiplayer(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that pressing the return key when selecting a construction for a settlement in a multiplayer game has the
        expected effect.
        """
        self.game_state.board.overlay.toggle_construction = MagicMock()
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.CONSTRUCTION]
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT
        self.game_state.board.game_config = self.TEST_MULTIPLAYER_CONFIG
        game_name = "Massive Multiplayer Game"
        self.game_state.board.game_name = game_name

        self.game_state.board.overlay.selected_construction = get_improvement("Melting Pot")
        self.game_state.players[0].resources = ResourceCollection(magma=5)
        on_key_return(self.game_controller, self.game_state)
        # The player should also have had their resources deducted.
        self.assertFalse(self.game_state.players[0].resources.magma)
        self.assertEqual(get_improvement("Melting Pot"), self.TEST_SETTLEMENT.current_work.construction)
        # Since this is a multiplayer game, we also expect an event with the appropriate attributes to have been
        # dispatched to the game server.
        expected_event = SetConstructionEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.SET_CONSTRUCTION,
                                              game_name, self.game_state.players[0].faction,
                                              self.game_state.players[0].resources, self.TEST_SETTLEMENT.name,
                                              self.TEST_SETTLEMENT.current_work)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)
        self.game_state.board.overlay.toggle_construction.assert_called_with([], [], [])

    def test_return_select_construction_none_selected(self):
        """
        Ensure that pressing the return key when selecting a construction for a settlement with none currently selected
        results in the overlay being removed.
        """
        self.game_state.board.overlay.toggle_construction = MagicMock()
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.CONSTRUCTION]
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT

        on_key_return(self.game_controller, self.game_state)

        # No current work should have been selected, but since the selected construction in the overlay was None, we do
        # expect the overlay to have been removed.
        self.assertIsNone(self.TEST_SETTLEMENT.current_work)
        self.game_state.board.overlay.toggle_construction.assert_called_with([], [], [])

    def test_return_select_blessing(self):
        """
        Ensure that pressing the return key when selecting a blessing confirms the selection.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.BLESSING]
        self.game_state.board.overlay.selected_blessing = BLESSINGS["beg_spl"]
        self.game_state.board.overlay.toggle_blessing = MagicMock()

        on_key_return(self.game_controller, self.game_state)
        self.assertEqual(BLESSINGS["beg_spl"], self.game_state.players[0].ongoing_blessing.blessing)
        self.game_state.board.overlay.toggle_blessing.assert_called_with([])

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_return_select_blessing_multiplayer(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that pressing the return key when selecting a blessing in a multiplayer game confirms the selection.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.BLESSING]
        self.game_state.board.overlay.selected_blessing = BLESSINGS["beg_spl"]
        self.game_state.board.overlay.toggle_blessing = MagicMock()
        self.game_state.board.game_config = self.TEST_MULTIPLAYER_CONFIG
        game_name = "Massive Multiplayer Game"
        self.game_state.board.game_name = game_name

        on_key_return(self.game_controller, self.game_state)
        expected_blessing = OngoingBlessing(BLESSINGS["beg_spl"])
        self.assertEqual(expected_blessing, self.game_state.players[0].ongoing_blessing)
        # Since this is a multiplayer game, we also expect an event with the appropriate attributes to have been
        # dispatched to the game server.
        expected_event = SetBlessingEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.SET_BLESSING, game_name,
                                          self.game_state.players[0].faction, expected_blessing)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)
        self.game_state.board.overlay.toggle_blessing.assert_called_with([])

    def test_return_attack_settlement_attacker_dies(self):
        """
        Ensure that the correct state and overlay modification occurs when pressing the return key to attack a
        settlement. In this instance, we expect the attacker unit to perish and the settlement to remain.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.SETL_CLICK]
        self.game_state.board.overlay.setl_attack_opt = SettlementAttackType.ATTACK
        self.game_state.board.overlay.toggle_setl_click = MagicMock()
        self.game_state.board.overlay.toggle_unit = MagicMock()
        self.game_state.board.overlay.toggle_setl_attack = MagicMock()

        # Setting up our combatants - note that TEST_UNIT and TEST_SETTLEMENT actually both belong to TEST_PLAYER. For
        # our purposes, it doesn't matter that a player's unit is attacking its own settlement.
        self.game_state.board.selected_unit = self.TEST_UNIT
        self.game_state.board.overlay.attacked_settlement = self.TEST_SETTLEMENT
        self.game_state.board.overlay.attacked_settlement_owner = self.TEST_PLAYER

        on_key_return(self.game_controller, self.game_state)
        self.game_state.board.overlay.toggle_setl_click.assert_called_with(None, None)
        # Since the unit died, we expect the player to no longer have any units, and the unit's overlay to be removed.
        self.assertFalse(self.TEST_PLAYER.units)
        self.assertIsNone(self.game_state.board.selected_unit)
        self.game_state.board.overlay.toggle_unit.assert_called_with(None)
        # We should also now see the settlement attack overlay.
        self.game_state.board.overlay.toggle_setl_attack.assert_called()
        self.assertFalse(self.game_state.board.attack_time_bank)

    def test_return_attack_besieged_settlement_taken(self):
        """
        Ensure that the correct state and overlay modification occurs when pressing the return key to attack an already
        besieged settlement. In this instance, we expect the attacker unit to succeed and take the settlement.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.SETL_CLICK]
        self.game_state.board.overlay.setl_attack_opt = SettlementAttackType.ATTACK
        self.game_state.board.overlay.toggle_setl_click = MagicMock()
        self.game_state.board.overlay.toggle_unit = MagicMock()
        self.game_state.board.overlay.toggle_setl_attack = MagicMock()

        # Setting up our combatants - we make sure that the unit will be able to take the settlement by setting the
        # settlement's strength to 1.
        self.game_state.board.selected_unit = self.TEST_UNIT
        self.game_state.board.overlay.attacked_settlement = self.TEST_SETTLEMENT
        self.game_state.board.overlay.attacked_settlement_owner = self.TEST_PLAYER_2
        self.TEST_SETTLEMENT.besieged = True
        self.TEST_SETTLEMENT.strength = 1
        self.TEST_UNIT.besieging = True
        self.TEST_PLAYER.settlements = []
        self.TEST_PLAYER.quads_seen = set()
        self.TEST_PLAYER_2.settlements = [self.TEST_SETTLEMENT]

        on_key_return(self.game_controller, self.game_state)
        self.game_state.board.overlay.toggle_setl_click.assert_called_with(None, None)
        # Now that the siege is over and the settlement has been taken, we expect the settlement and unit to reflect
        # that.
        self.assertFalse(self.TEST_SETTLEMENT.besieged)
        self.assertFalse(self.TEST_UNIT.besieging)
        # The settlement should have changed hands.
        self.assertTrue(self.TEST_PLAYER.settlements)
        self.assertFalse(self.TEST_PLAYER_2.settlements)
        # The player that took the settlement should now also have the quads around the settlement marked as seen.
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        # We should also now see the settlement attack overlay.
        self.game_state.board.overlay.toggle_setl_attack.assert_called()
        self.assertFalse(self.game_state.board.attack_time_bank)

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_return_attack_settlement_multiplayer(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the correct state and overlay modification occurs when pressing the return key to attack a
        settlement in a multiplayer game.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.SETL_CLICK]
        self.game_state.board.overlay.setl_attack_opt = SettlementAttackType.ATTACK
        self.game_state.board.overlay.toggle_setl_click = MagicMock()
        self.game_state.board.overlay.toggle_unit = MagicMock()
        self.game_state.board.overlay.toggle_setl_attack = MagicMock()
        self.game_state.board.game_config = self.TEST_MULTIPLAYER_CONFIG
        game_name = "Massive Multiplayer Game"
        self.game_state.board.game_name = game_name

        # Setting up our combatants - note that TEST_UNIT and TEST_SETTLEMENT actually both belong to TEST_PLAYER. For
        # our purposes, it doesn't matter that a player's unit is attacking its own settlement.
        self.TEST_UNIT.health = 100
        self.game_state.board.selected_unit = self.TEST_UNIT
        self.game_state.board.overlay.attacked_settlement = self.TEST_SETTLEMENT
        self.game_state.board.overlay.attacked_settlement_owner = self.TEST_PLAYER

        on_key_return(self.game_controller, self.game_state)
        # We don't expect either the attacking unit to have died or the settlement to have been taken.
        self.game_state.board.overlay.toggle_setl_click.assert_called_with(None, None)
        # Since this is a multiplayer game, we also expect an event with the appropriate attributes to have been
        # dispatched to the game server.
        expected_event = AttackSettlementEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.ATTACK_SETTLEMENT,
                                               game_name, self.TEST_PLAYER.faction, self.TEST_UNIT.location,
                                               self.TEST_SETTLEMENT.name)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)
        # We should also now see the settlement attack overlay.
        self.game_state.board.overlay.toggle_setl_attack.assert_called()
        self.assertFalse(self.game_state.board.attack_time_bank)

    def test_return_besiege_settlement(self):
        """
        Ensure that the correct state and overlay modification occurs when pressing the return key to besiege a
        settlement.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.SETL_CLICK]
        self.game_state.board.overlay.setl_attack_opt = SettlementAttackType.BESIEGE
        self.game_state.board.overlay.toggle_setl_click = MagicMock()

        self.game_state.board.selected_unit = self.TEST_UNIT
        self.game_state.board.overlay.attacked_settlement = self.TEST_SETTLEMENT

        on_key_return(self.game_controller, self.game_state)
        self.assertTrue(self.TEST_UNIT.besieging)
        self.assertTrue(self.TEST_SETTLEMENT.besieged)
        self.game_state.board.overlay.toggle_setl_click.assert_called_with(None, None)

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_return_besiege_settlement_multiplayer(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the correct state and overlay modification occurs when pressing the return key to besiege a
        settlement in a multiplayer game.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.SETL_CLICK]
        self.game_state.board.overlay.setl_attack_opt = SettlementAttackType.BESIEGE
        self.game_state.board.overlay.toggle_setl_click = MagicMock()
        self.game_state.board.game_config = self.TEST_MULTIPLAYER_CONFIG
        game_name = "Massive Multiplayer Game"
        self.game_state.board.game_name = game_name

        self.game_state.board.selected_unit = self.TEST_UNIT
        self.game_state.board.overlay.attacked_settlement = self.TEST_SETTLEMENT

        on_key_return(self.game_controller, self.game_state)
        self.assertTrue(self.TEST_UNIT.besieging)
        self.assertTrue(self.TEST_SETTLEMENT.besieged)
        # Since this is a multiplayer game, we also expect an event with the appropriate attributes to have been
        # dispatched to the game server.
        expected_event = BesiegeSettlementEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.BESIEGE_SETTLEMENT,
                                                game_name, self.TEST_PLAYER.faction, self.TEST_UNIT.location,
                                                self.TEST_SETTLEMENT.name)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)
        self.game_state.board.overlay.toggle_setl_click.assert_called_with(None, None)

    def test_return_leave_settlement_click_overlay(self):
        """
        Ensure that the settlement click overlay is removed when the return key is pressed and the cancel button is
        selected in the overlay.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.SETL_CLICK]
        self.game_state.board.overlay.setl_attack_opt = None
        self.game_state.board.overlay.toggle_setl_click = MagicMock()

        on_key_return(self.game_controller, self.game_state)
        self.game_state.board.overlay.toggle_setl_click.assert_called_with(None, None)

    def test_return_select_pause_option_resume(self):
        """
        Ensure that the pause overlay is toggled when its resume option is selected and the return key is pressed.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.PAUSE]
        self.game_state.board.overlay.pause_option = PauseOption.RESUME
        self.game_state.board.overlay.toggle_pause = MagicMock()
        on_key_return(self.game_controller, self.game_state)
        self.game_state.board.overlay.toggle_pause.assert_called()

    @patch("source.game_management.game_input_handler.save_game")
    def test_return_select_pause_option_save(self, save_mock: MagicMock):
        """
        Ensure that the game is saved and the pause overlay updated when the return key is pressed with the save game
        option selected.
        :param save_mock: The mock implementation of the save_game() function.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.PAUSE]
        self.game_state.board.overlay.pause_option = PauseOption.SAVE

        self.assertFalse(self.game_state.board.overlay.has_saved)
        on_key_return(self.game_controller, self.game_state)
        save_mock.assert_called_with(self.game_state)
        self.assertTrue(self.game_state.board.overlay.has_saved)

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_return_select_pause_option_save_multiplayer(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the game is saved and the pause overlay updated when the return key is pressed with the save game
        option selected in a multiplayer game.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.PAUSE]
        self.game_state.board.overlay.pause_option = PauseOption.SAVE
        self.game_state.board.game_config = self.TEST_MULTIPLAYER_CONFIG
        game_name = "Massive Multiplayer Game"
        self.game_state.board.game_name = game_name

        self.assertFalse(self.game_state.board.overlay.has_saved)
        on_key_return(self.game_controller, self.game_state)
        # Since this is a multiplayer game, we also expect an event with the appropriate attributes to have been
        # dispatched to the game server.
        expected_event = SaveEvent(EventType.SAVE, self.TEST_IDENTIFIER, game_name)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)
        self.assertTrue(self.game_state.board.overlay.has_saved)

    def test_return_select_pause_option_controls(self):
        """
        Ensure that the controls overlay is toggled when the return key is pressed with the controls option in the
        pause overlay selected.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.PAUSE]
        self.game_state.board.overlay.pause_option = PauseOption.CONTROLS
        self.game_state.board.overlay.toggle_controls = MagicMock()

        on_key_return(self.game_controller, self.game_state)
        self.assertFalse(self.game_state.board.overlay.show_additional_controls)
        self.game_state.board.overlay.toggle_controls.assert_called()

    def test_return_select_pause_option_quit(self):
        """
        Ensure that the player returns to the main menu after pressing the return key when in the pause overlay with the
        quit option selected.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.PAUSE]
        self.game_state.board.overlay.pause_option = PauseOption.QUIT
        self.game_controller.music_player.stop_game_music = MagicMock()
        self.game_controller.music_player.play_menu_music = MagicMock()

        self.assertFalse(self.game_state.on_menu)
        on_key_return(self.game_controller, self.game_state)
        self.assertFalse(self.game_state.game_started)
        self.assertTrue(self.game_state.on_menu)
        self.assertIsNone(self.game_state.board)
        self.assertFalse(self.game_state.players)
        self.assertFalse(self.game_controller.menu.loading_game)
        self.assertFalse(self.game_controller.menu.loading_game_multiplayer_status)
        self.assertFalse(self.game_controller.menu.in_game_setup)
        self.assertIsNone(self.game_controller.menu.multiplayer_lobby)
        self.assertFalse(self.game_controller.menu.joining_game)
        self.assertFalse(self.game_controller.menu.viewing_lobbies)
        self.assertFalse(self.game_controller.menu.viewing_local_lobbies)
        self.assertFalse(self.game_controller.menu.faction_idx)
        self.assertEqual(MainMenuOption.NEW_GAME, self.game_controller.menu.main_menu_option)
        self.game_controller.music_player.stop_game_music.assert_called()
        self.game_controller.music_player.play_menu_music.assert_called()

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_return_select_pause_option_quit_multiplayer(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the player returns to the main menu after pressing the return key when in the pause overlay with the
        quit option selected, in a multiplayer game.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.PAUSE]
        self.game_state.board.overlay.pause_option = PauseOption.QUIT
        self.game_controller.music_player.stop_game_music = MagicMock()
        self.game_controller.music_player.play_menu_music = MagicMock()
        self.game_state.board.game_config = self.TEST_MULTIPLAYER_CONFIG
        lobby_name = "Large Lobby"
        # Obviously this lobby is not realistic since it has no players, but it's enough for our testing purposes.
        self.game_controller.menu.multiplayer_lobby = LobbyDetails(lobby_name, [], self.TEST_MULTIPLAYER_CONFIG, 99)

        self.assertFalse(self.game_state.on_menu)
        on_key_return(self.game_controller, self.game_state)
        # Since this is a multiplayer game, we also expect an event with the appropriate attributes to have been
        # dispatched to the game server.
        expected_event = LeaveEvent(EventType.LEAVE, self.TEST_IDENTIFIER, lobby_name)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)
        self.assertFalse(self.game_state.game_started)
        self.assertTrue(self.game_state.on_menu)
        self.assertIsNone(self.game_state.board)
        self.assertFalse(self.game_state.players)
        self.assertFalse(self.game_controller.menu.loading_game)
        self.assertFalse(self.game_controller.menu.loading_game_multiplayer_status)
        self.assertFalse(self.game_controller.menu.in_game_setup)
        self.assertIsNone(self.game_controller.menu.multiplayer_lobby)
        self.assertFalse(self.game_controller.menu.joining_game)
        self.assertFalse(self.game_controller.menu.viewing_lobbies)
        self.assertFalse(self.game_controller.menu.viewing_local_lobbies)
        self.assertFalse(self.game_controller.menu.faction_idx)
        self.assertEqual(MainMenuOption.NEW_GAME, self.game_controller.menu.main_menu_option)
        self.game_controller.music_player.stop_game_music.assert_called()
        self.game_controller.music_player.play_menu_music.assert_called()

    def test_return_deploy_from_unit(self):
        """
        Ensure that pressing the return key when viewing a deployer unit's passengers triggers the deployment process to
        begin.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.UNIT]
        self.game_state.board.overlay.show_unit_passengers = True

        self.assertFalse(self.game_state.board.deploying_army_from_unit)
        self.assertFalse(self.game_state.board.overlay.is_deployment())
        on_key_return(self.game_controller, self.game_state)
        self.assertTrue(self.game_state.board.deploying_army_from_unit)
        self.assertTrue(self.game_state.board.overlay.is_deployment())

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_return_end_turn_multiplayer(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the correct state updates occur and the correct events are dispatched when pressing the return key
        to end a turn in a multiplayer game.
        """
        self.game_state.game_started = True
        # We mock out the warning check because it's not materially relevant to this test.
        self.game_state.check_for_warnings = MagicMock(return_value=False)
        self.game_state.board.game_config = self.TEST_MULTIPLAYER_CONFIG
        game_name = "Massive Multiplayer Game"
        self.game_state.board.game_name = game_name

        # To begin with, let's simulate a case where the current turn is already being processed by the game server.
        self.game_state.processing_turn = True
        self.game_state.board.waiting_for_other_players = False
        on_key_return(self.game_controller, self.game_state)
        # Since the turn is being processed, we expect no state change and no event to be dispatched.
        self.assertFalse(self.game_state.board.waiting_for_other_players)
        dispatch_mock.assert_not_called()

        # Now, let's simulate the standard end turn case.
        self.game_state.processing_turn = False
        self.game_state.board.waiting_for_other_players = False
        on_key_return(self.game_controller, self.game_state)
        # We expect state to have changed, and an end turn event to have been dispatched, signalling that the player is
        # ready for the turn to end.
        self.assertTrue(self.game_state.board.waiting_for_other_players)
        expected_event = EndTurnEvent(EventType.END_TURN, self.TEST_IDENTIFIER, game_name)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)

        # Lastly, let's consider the unready case.
        self.game_state.processing_turn = False
        self.game_state.board.waiting_for_other_players = True
        on_key_return(self.game_controller, self.game_state)
        # We expect state to have changed, and an unready event to have been dispatched, signalling that the player is
        # no longer ready for the turn to end.
        self.assertFalse(self.game_state.board.waiting_for_other_players)
        expected_event = UnreadyEvent(EventType.UNREADY, self.TEST_IDENTIFIER, game_name)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)

    @patch("source.game_management.game_input_handler.save_stats_achievements")
    @patch("source.game_management.game_input_handler.save_game")
    def test_return_end_turn(self, save_mock: MagicMock, save_stats_achievements_mock: MagicMock):
        """
        Ensure that the correct state updates occur when pressing the return key to end a turn.
        :param save_mock: The mock implementation of the save_game() function.
        :param save_stats_achievements_mock: The mock implementation of the save_stats_achievements() function.
        """
        self.game_state.game_started = True
        # We mock out our complex game state functions here to avoid any potential issues.
        self.game_state.end_turn = MagicMock(return_value=True)
        self.game_state.board.overlay.toggle_ach_notif = MagicMock()
        self.game_state.process_heathens = MagicMock()
        self.game_state.process_ais = MagicMock()
        self.game_controller.last_turn_time = 0
        save_stats_achievements_mock.return_value = ACHIEVEMENTS[0:2]
        # The below is an incorrect value, but we set it to this in order to verify that the value is updated at the end
        # of each turn.
        self.game_state.board.overlay.total_settlement_count = 2

        on_key_return(self.game_controller, self.game_state)
        save_mock.assert_called_with(self.game_state, auto=True)
        self.assertTrue(self.game_controller.last_turn_time)
        save_stats_achievements_mock.assert_called()
        self.game_state.board.overlay.toggle_ach_notif.assert_called_with(ACHIEVEMENTS[0:2])
        self.assertEqual(3, self.game_state.board.overlay.total_settlement_count)
        self.game_state.process_heathens.assert_called()
        self.game_state.process_ais.assert_called_with(self.game_controller.move_maker)

    def test_shift(self):
        """
        Ensure that the correct overlay toggle occurs when the shift key is pressed.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.remove_warning_if_possible = MagicMock()
        self.game_state.board.overlay.toggle_standard = MagicMock()

        on_key_shift(self.game_state)
        self.game_state.board.overlay.remove_warning_if_possible.assert_called()
        self.game_state.board.overlay.toggle_standard.assert_called()

    def test_c(self):
        """
        Ensure that the correct overlay toggle occurs when the C key is pressed.
        """
        self.game_state.game_started = True
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT
        self.game_state.board.overlay.toggle_construction = MagicMock()

        # We need to retrieve the improvements and unit plans ourselves first to compare them to the actual call.
        expected_improvements = get_available_improvements(self.TEST_PLAYER, self.TEST_SETTLEMENT)
        expected_unit_plans = get_available_unit_plans(self.TEST_PLAYER, self.TEST_SETTLEMENT)

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

        self.game_state.board.overlay.current_standard_overlay_view = StandardOverlayView.VAULT
        # To begin with, the test player is on the vault view of the standard overlay, so pressing the F key should have
        # no effect.
        on_key_f(self.game_controller, self.game_state)
        self.game_state.board.overlay.toggle_blessing.assert_not_called()

        self.game_state.board.overlay.current_standard_overlay_view = StandardOverlayView.BLESSINGS
        # Now since the test player is on the blessings view and hasn't completed any blessings, every blessing is
        # displayed.
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
        self.assertEqual(1, self.game_state.board.overlay.toggle_deployment.call_count)

        # We also expect to be able to abort the deployment if we want to, by pressing the D key again.
        on_key_d(self.game_state)
        self.assertFalse(self.game_state.board.deploying_army)
        self.assertEqual(2, self.game_state.board.overlay.toggle_deployment.call_count)

    def test_d_deployment_from_unit(self):
        """
        Ensure that the D key correctly toggles the passenger view for deployer units.
        """
        test_deployer_unit_plan = DeployerUnitPlan(0, 1, 2, "3", None, 4)
        test_deployer_unit = DeployerUnit(1, 2, (3, 4), False, test_deployer_unit_plan)
        self.game_state.game_started = True
        self.game_state.board.selected_unit = test_deployer_unit
        self.game_state.players[0].units.append(test_deployer_unit)
        self.game_state.board.overlay.show_unit_passengers = False

        # The toggle shouldn't occur if the deployer unit doesn't have any passengers.
        on_key_d(self.game_state)
        self.assertFalse(self.game_state.board.overlay.show_unit_passengers)

        # Now that the deployer unit has a passenger, the toggle should occur.
        test_deployer_unit.passengers = [self.TEST_UNIT]
        on_key_d(self.game_state)
        self.assertTrue(self.game_state.board.overlay.show_unit_passengers)

    def test_x_disband(self):
        """
        Ensure that the X key correctly disbands the selected unit and credits the player.
        """
        self.game_state.game_started = True
        self.game_state.board.selected_unit = self.TEST_PLAYER.units[0]
        self.game_state.board.overlay.toggle_unit = MagicMock()

        self.assertEqual(self.PLAYER_WEALTH, self.TEST_PLAYER.wealth)
        self.assertTrue(self.TEST_PLAYER.units)
        on_key_x(self.game_state)
        # The player should now have their wealth increased by the value of the unit.
        self.assertEqual(self.PLAYER_WEALTH + UNIT_PLANS[0].cost, self.TEST_PLAYER.wealth)
        # Additionally, the player only had one unit, so they should now have no units.
        self.assertFalse(self.TEST_PLAYER.units)
        # Lastly, the unit should have been unselected and the overlay removed.
        self.assertIsNone(self.game_state.board.selected_unit)
        self.game_state.board.overlay.toggle_unit.assert_called_with(None)

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_x_disband_multiplayer(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the X key correctly disbands the selected unit and credits the player in a multiplayer game.
        """
        self.game_state.game_started = True
        self.game_state.board.selected_unit = self.TEST_UNIT
        self.game_state.board.overlay.toggle_unit = MagicMock()
        self.game_state.board.game_config = self.TEST_MULTIPLAYER_CONFIG
        game_name = "Massive Multiplayer Game"
        self.game_state.board.game_name = game_name

        self.assertEqual(self.PLAYER_WEALTH, self.TEST_PLAYER.wealth)
        self.assertTrue(self.TEST_PLAYER.units)
        on_key_x(self.game_state)
        # The player should now have their wealth increased by the value of the unit.
        self.assertEqual(self.PLAYER_WEALTH + UNIT_PLANS[0].cost, self.TEST_PLAYER.wealth)
        # Additionally, the player only had one unit, so they should now have no units.
        self.assertFalse(self.TEST_PLAYER.units)
        # Lastly, the unit should have been unselected and the overlay removed.
        self.assertIsNone(self.game_state.board.selected_unit)
        self.game_state.board.overlay.toggle_unit.assert_called_with(None)
        # Since this is a multiplayer game, we also expect an event with the appropriate attributes to have been
        # dispatched to the game server.
        expected_event = DisbandUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.DISBAND_UNIT,
                                          game_name, self.TEST_PLAYER.faction, self.TEST_UNIT.location)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)

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

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_space_menu_multiplayer_lobby(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the correct event is dispatched to the game server and the correct state changes when pressing the
        space key while in a multiplayer lobby.
        """
        self.game_state.on_menu = True
        lobby_name = "Large Lobby"
        # Obviously this lobby is not realistic since it has no players, but it's enough for our testing purposes.
        self.game_controller.menu.multiplayer_lobby = LobbyDetails(lobby_name, [], self.TEST_MULTIPLAYER_CONFIG, 99)

        on_key_space(self.game_controller, self.game_state)
        # An event should have been dispatched to the game server.
        expected_event = LeaveEvent(EventType.LEAVE, self.TEST_IDENTIFIER, lobby_name)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)
        # The lobby and game state should also have been reset in state.
        self.assertIsNone(self.game_controller.menu.multiplayer_lobby)
        self.assertIsNone(self.game_state.board)
        self.assertFalse(self.game_state.players)

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

    def test_space_menu_loading_multiplayer_game(self):
        """
        Ensure that the player is returned to the menu when pressing the space key while viewing available multiplayer
        game saves.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.loading_game = True
        self.game_controller.menu.loading_game_multiplayer_status = MultiplayerStatus.GLOBAL
        on_key_space(self.game_controller, self.game_state)
        self.assertFalse(self.game_controller.menu.loading_game)
        self.assertFalse(self.game_controller.menu.loading_game_multiplayer_status)

    def test_space_menu_joining_existing_game(self):
        """
        Ensure that the player is returned to the lobby selection menu when pressing the space key while in a
        multiplayer lobby that they have just joined.
        """
        self.game_state.on_menu = True
        # In this simulated case, the player was just viewing the lobbies before they joined one.
        self.game_controller.menu.viewing_lobbies = True
        self.game_controller.menu.joining_game = True
        on_key_space(self.game_controller, self.game_state)
        self.assertFalse(self.game_controller.menu.joining_game)

    def test_space_menu_joining_loaded_game(self):
        """
        Ensure that the player is returned to the load game menu when pressing the space key while in a multiplayer
        lobby that they have just loaded.
        """
        self.game_state.on_menu = True
        # In this simulated case, the player was just viewing the available multiplayer game saves before they joined
        # one. When a player loads a game in this way, once they are 'joining' it, loading_game is set to False.
        self.game_controller.menu.loading_game = False
        self.game_controller.menu.loading_game_multiplayer_status = MultiplayerStatus.GLOBAL
        self.game_controller.menu.joining_game = True
        on_key_space(self.game_controller, self.game_state)
        self.assertFalse(self.game_controller.menu.joining_game)
        # Since the player loaded a game, we expect state to be updated so that the available multiplayer games to load
        # are once again displayed.
        self.assertTrue(self.game_controller.menu.loading_game)

    def test_space_menu_viewing_lobbies(self):
        """
        Ensure that the player is returned to the menu when pressing the space key while viewing the available
        multiplayer game lobbies.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.viewing_lobbies = True
        on_key_space(self.game_controller, self.game_state)
        self.assertFalse(self.game_controller.menu.viewing_lobbies)
        self.assertFalse(self.game_controller.menu.viewing_local_lobbies)

    def test_space_menu_statistics(self):
        """
        Ensure that the player is returned to the menu when pressing the space key while viewing their statistics.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.viewing_stats = True
        on_key_space(self.game_controller, self.game_state)
        self.assertFalse(self.game_controller.menu.viewing_stats)

    def test_space_menu_achievements(self):
        """
        Ensure that the player is returned to the menu when pressing the space key while viewing their achievements.
        """
        self.game_state.on_menu = True
        self.game_controller.menu.viewing_achievements = True
        on_key_space(self.game_controller, self.game_state)
        self.assertFalse(self.game_controller.menu.viewing_achievements)

    def test_space_overlay(self):
        """
        Ensure that the space key correctly toggles in-game intrusive overlays.
        """

        def test_overlay(test_class: GameInputHandlerTest,
                         overlay_type: OverlayType,
                         fn_to_mock: str,
                         expected_args: Optional[list]):
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
        test_overlay(self, OverlayType.ACH_NOTIF, "toggle_ach_notif", [[]])
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

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_a_autofill_multiplayer_lobby(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the A key autofills the appropriate multiplayer lobbies.
        """
        self.game_state.on_menu = True
        lobby_name = "Large Lobby"

        # To begin with, let's simulate a situation where the lobby is already full. Since we're using an unrealistic
        # lobby with zero players, we'll just set the game config player count to zero.
        zero_player_config = GameConfig(0, Faction.AGRICULTURISTS, True, True, True, MultiplayerStatus.GLOBAL)
        self.game_controller.menu.multiplayer_lobby = LobbyDetails(lobby_name, [], zero_player_config, 99)
        on_key_a(self.game_controller, self.game_state)
        # Since we're technically already at the max player count, no event to autofill the lobby should have been
        # dispatched to the game server.
        dispatch_mock.assert_not_called()

        # Now, if we use the standard test multiplayer config, which has a player count of two, we expect an event to be
        # dispatched.
        self.game_controller.menu.multiplayer_lobby = LobbyDetails(lobby_name, [], self.TEST_MULTIPLAYER_CONFIG, 99)
        on_key_a(self.game_controller, self.game_state)
        expected_event = AutofillEvent(EventType.AUTOFILL, self.TEST_IDENTIFIER, lobby_name)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)

    def test_a_construction(self):
        """
        Ensure that the A key automatically selects a construction for the selected settlement.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.SETTLEMENT]
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT

        self.assertIsNone(self.TEST_SETTLEMENT.current_work)
        on_key_a(self.game_controller, self.game_state)
        self.assertIsNotNone(self.TEST_SETTLEMENT.current_work)

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_a_construction_multiplayer(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the A key automatically selects a construction for the selected settlement in a multiplayer game.
        """
        self.game_state.game_started = True
        self.game_state.board.overlay.showing = [OverlayType.SETTLEMENT]
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT
        self.game_state.board.game_config = self.TEST_MULTIPLAYER_CONFIG
        game_name = "Massive Multiplayer Game"
        self.game_state.board.game_name = game_name

        self.assertIsNone(self.TEST_SETTLEMENT.current_work)
        on_key_a(self.game_controller, self.game_state)
        self.assertIsNotNone(self.TEST_SETTLEMENT.current_work)
        # Since this is a multiplayer game, we also expect an event with the appropriate attributes to have been
        # dispatched to the game server.
        expected_event = SetConstructionEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.SET_CONSTRUCTION,
                                              game_name, self.game_state.players[0].faction,
                                              self.game_state.players[0].resources, self.TEST_SETTLEMENT.name,
                                              self.TEST_SETTLEMENT.current_work)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)

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
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT
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
        test_settlement = Settlement("Projecton", (60, 60), [], [], ResourceCollection(), [],
                                     current_work=Construction(PROJECTS[0]))
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

    @patch("source.game_management.game_input_handler.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("source.game_management.game_input_handler.dispatch_event")
    def test_b_buyout_success_multiplayer(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that the B key successfully buys out a settlement's current work when the appropriate criteria are met
        in a multiplayer game.
        """
        initial_work: Construction = self.TEST_SETTLEMENT_WITH_WORK.current_work
        self.game_state.game_started = True
        self.game_state.board.selected_settlement = self.TEST_SETTLEMENT_WITH_WORK
        self.game_state.board.overlay.toggle_construction_notification = MagicMock()
        self.game_state.board.game_config = self.TEST_MULTIPLAYER_CONFIG
        game_name = "Massive Multiplayer Game"
        self.game_state.board.game_name = game_name

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
        # Since this is a multiplayer game, we also expect an event with the appropriate attributes to have been
        # dispatched to the game server.
        expected_event = BuyoutConstructionEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                 UpdateAction.BUYOUT_CONSTRUCTION,
                                                 game_name, self.game_state.players[0].faction,
                                                 self.TEST_SETTLEMENT_WITH_WORK.name, self.game_state.players[0].wealth)
        dispatch_mock.assert_called_with(expected_event,
                                         self.TEST_EVENT_DISPATCHERS,
                                         self.TEST_MULTIPLAYER_CONFIG.multiplayer)

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
        self.game_state.board.overlay.remove_warning_if_possible = MagicMock()
        self.game_state.board.overlay.toggle_settlement = MagicMock()
        self.game_state.board.overlay.update_settlement = MagicMock()
        self.game_state.board.overlay.toggle_unit = MagicMock()
        # Slightly change the order of the settlements to make this test's demonstration simpler.
        self.TEST_PLAYER.settlements = [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_WITH_WORK, self.TEST_SETTLEMENT_2]
        # Set up a situation where the player has one of their units selected.
        self.game_state.board.overlay.showing = [OverlayType.UNIT]
        self.game_state.board.selected_unit = self.TEST_UNIT

        on_key_j(self.game_state)
        self.game_state.board.overlay.remove_warning_if_possible.assert_called()
        # We firstly expect the selected unit to now be deselected, and the unit overlay removed.
        self.assertIsNone(self.game_state.board.selected_unit)
        self.game_state.board.overlay.toggle_unit.assert_called_with(None)
        # Having not had any settlement selected beforehand, after the first press, the first settlement should be
        # selected and centred, with its overlay displayed.
        self.assertEqual(self.TEST_SETTLEMENT, self.game_state.board.selected_settlement)
        self.game_state.board.overlay.toggle_settlement.assert_called_with(self.TEST_SETTLEMENT, self.TEST_PLAYER)
        self.assertTupleEqual((self.TEST_SETTLEMENT.location[0] - 12, self.TEST_SETTLEMENT.location[1] - 11),
                              self.game_state.map_pos)

        on_key_j(self.game_state)
        self.assertEqual(2, self.game_state.board.overlay.remove_warning_if_possible.call_count)
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
        self.assertEqual(3, self.game_state.board.overlay.remove_warning_if_possible.call_count)
        self.assertEqual(self.TEST_SETTLEMENT, self.game_state.board.selected_settlement)
        self.game_state.board.overlay.update_settlement.assert_called_with(self.TEST_SETTLEMENT)
        self.assertTupleEqual((self.TEST_SETTLEMENT.location[0] - 12, self.TEST_SETTLEMENT.location[1] - 11),
                              self.game_state.map_pos)


if __name__ == '__main__':
    unittest.main()
