import datetime
import json
import sched
import socket
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Thread
from typing import List, Dict, Tuple
from unittest.mock import MagicMock, call, patch

from source.display.board import Board
from source.display.menu import Menu, SetupOption
from source.display.overlay import Overlay
from source.foundation.catalogue import LOBBY_NAMES, PLAYER_NAMES, FACTION_COLOURS, BLESSINGS, PROJECTS, IMPROVEMENTS, \
    UNIT_PLANS, Namer, get_heathen_plan, ACHIEVEMENTS
from source.foundation.models import PlayerDetails, Faction, GameConfig, Player, Settlement, ResourceCollection, \
    OngoingBlessing, Construction, InvestigationResult, Unit, DeployerUnit, Quad, Biome, AIPlaystyle, \
    ExpansionPlaystyle, AttackPlaystyle, LobbyDetails, Heathen, Victory, VictoryType, MultiplayerStatus
from source.game_management.game_controller import GameController
from source.game_management.game_state import GameState
from source.game_management.movemaker import MoveMaker
from source.networking.client import GLOBAL_SERVER_HOST, SERVER_PORT, EventDispatcher, DispatcherKind
from source.networking.event_listener import RequestHandler, MicrocosmServer, EventListener
from source.networking.events import EventType, RegisterEvent, Event, CreateEvent, InitEvent, UpdateEvent, \
    UpdateAction, QueryEvent, LeaveEvent, JoinEvent, EndTurnEvent, UnreadyEvent, AutofillEvent, SaveEvent, \
    QuerySavesEvent, LoadEvent, FoundSettlementEvent, SetBlessingEvent, SetConstructionEvent, MoveUnitEvent, \
    DeployUnitEvent, GarrisonUnitEvent, InvestigateEvent, BesiegeSettlementEvent, BuyoutConstructionEvent, \
    DisbandUnitEvent, AttackUnitEvent, AttackSettlementEvent, HealUnitEvent, BoardDeployerEvent, DeployerDeployEvent
from source.saving.save_encoder import SaveEncoder, ObjectConverter
from source.util.minifier import minify_quad, minify_player, minify_quads_seen, minify_heathens


class EventListenerTest(unittest.TestCase):
    """
    The test class for event_listener.py.
    """
    TEST_IDENTIFIER: int = 123
    TEST_IDENTIFIER_2: int = 456
    TEST_HOST: str = "127.0.0.1"
    TEST_HOST_2: str = "192.168.0.1"
    TEST_PORT: int = 9999
    TEST_PORT_2: int = 8888
    TEST_EVENT: Event = Event(EventType.KEEPALIVE, TEST_IDENTIFIER)
    TEST_EVENT_BYTES: bytes = b'{"type":"KEEPALIVE","identifier":123}'
    TEST_GAME_NAME: str = "My favourite game"
    TEST_GAME_CONFIG: GameConfig = GameConfig(2, Faction.AGRICULTURISTS, True, True, True, MultiplayerStatus.GLOBAL)

    @patch("source.game_management.game_controller.MusicPlayer")
    def setUp(self, _: MagicMock):
        """
        Set up some test models, our mock server, and request handler - noting that the call of the handler's
        constructor actually handles the test event given in the request. Note that we mock out MusicPlayer so that the
        construction of the GameController doesn't try to play the menu music.
        """
        self.TEST_QUAD: Quad = Quad(Biome.FOREST, 0, 0, 0, 0, (0, 0))
        self.TEST_QUAD_2: Quad = Quad(Biome.MOUNTAIN, 0, 0, 0, 0, (5, 5))
        self.TEST_SETTLEMENT: Settlement = \
            Settlement("Testville", (0, 0), [], [self.TEST_QUAD], ResourceCollection(), [])
        self.TEST_SETTLEMENT_2: Settlement = \
            Settlement("EvilTown", (5, 5), [], [self.TEST_QUAD_2], ResourceCollection(), [])
        self.TEST_UNIT: Unit = Unit(50.0, 2, (4, 4), False, deepcopy(UNIT_PLANS[0]))
        self.TEST_UNIT_2: Unit = Unit(50.0, 2, (8, 8), False, deepcopy(UNIT_PLANS[0]))
        # The unit plan used is the first one that can heal.
        self.TEST_HEALER_UNIT: Unit = Unit(20.0, 20, (5, 5), False, deepcopy(UNIT_PLANS[6]))
        # The unit plan used is the first deployer one.
        self.TEST_DEPLOYER_UNIT: DeployerUnit = DeployerUnit(60.0, 60, (6, 6), False, deepcopy(UNIT_PLANS[9]))
        # The unit plan used is the settler unit plan.
        self.TEST_SETTLER_UNIT: Unit = Unit(5.0, 5, (7, 7), False, deepcopy(UNIT_PLANS[3]))
        self.TEST_HEATHEN: Heathen = Heathen(40.0, 3, (9, 9), get_heathen_plan(0))
        self.TEST_GAME_STATE: GameState = GameState()
        self.TEST_GAME_STATE.players = [
            Player("Uno", Faction.AGRICULTURISTS, FACTION_COLOURS[Faction.AGRICULTURISTS],
                   settlements=[self.TEST_SETTLEMENT], units=[self.TEST_UNIT]),
            Player("Dos", Faction.FRONTIERSMEN, FACTION_COLOURS[Faction.FRONTIERSMEN],
                   settlements=[self.TEST_SETTLEMENT_2])
        ]
        self.TEST_GAME_STATE.heathens = [self.TEST_HEATHEN]
        self.TEST_GAME_CONTROLLER: GameController = GameController()

        self.mock_socket: MagicMock = MagicMock()
        self.mock_server: MicrocosmServer = MagicMock()
        self.mock_server.game_clients_ref = {
            self.TEST_GAME_NAME: [PlayerDetails("Uno", Faction.AGRICULTURISTS, self.TEST_IDENTIFIER),
                                  PlayerDetails("Dos", Faction.FRONTIERSMEN, self.TEST_IDENTIFIER_2)]
        }
        self.mock_server.clients_ref = {
            self.TEST_IDENTIFIER: (self.TEST_HOST, self.TEST_PORT),
            self.TEST_IDENTIFIER_2: (self.TEST_HOST_2, self.TEST_PORT_2)
        }
        self.mock_server.namers_ref = {}
        self.mock_server.move_makers_ref = {}
        self.mock_server.lobbies_ref = {
            self.TEST_GAME_NAME: self.TEST_GAME_CONFIG
        }
        self.mock_server.game_states_ref = {}
        self.mock_server.game_controller_ref = self.TEST_GAME_CONTROLLER
        self.mock_server.keepalive_ctrs_ref = {}
        self.request_handler: RequestHandler = RequestHandler((self.TEST_EVENT_BYTES, self.mock_socket),
                                                              (self.TEST_HOST, self.TEST_PORT), self.mock_server)

    def test_handle(self):
        """
        Ensure that requests are handled correctly.
        """
        self.request_handler.process_event = MagicMock()
        self.request_handler.handle()
        # We can't just assert on the call itself, since the serialised event is turned into an ObjectConverter object,
        # rather than an actual Event.
        event_processed: Event = self.request_handler.process_event.call_args[0][0]
        socket_processed: socket.socket = self.request_handler.process_event.call_args[0][1]
        self.assertEqual(self.TEST_EVENT.type, event_processed.type)
        self.assertEqual(self.TEST_EVENT.identifier, event_processed.identifier)
        self.assertEqual(self.mock_socket, socket_processed)

    def test_handle_syntactically_incorrect(self):
        """
        Ensure that requests that are not syntactically valid don't get processed.
        """
        # The below is invalid unicode.
        self.request_handler.request = b"F\xc3\xb8\xc3\xb6\xbbB\xc3\xa5r", self.mock_socket
        self.request_handler.process_event = MagicMock()
        self.request_handler.handle()
        self.request_handler.process_event.assert_not_called()

        # The below is invalid JSON.
        self.request_handler.request = b"{ not valid }", self.mock_socket
        self.request_handler.process_event = MagicMock()
        self.request_handler.handle()
        self.request_handler.process_event.assert_not_called()

    def test_forward_packet(self):
        """
        Ensure that packets are correctly forwarded to the correct clients under the correct conditions.
        """
        # We need to disable the pylint rule against protected access since we're going to be testing an internal method
        # in this test.
        # pylint: disable=protected-access
        self.request_handler._forward_packet(self.TEST_EVENT, self.TEST_GAME_NAME, self.mock_socket)
        # We expect the packet to have been forwarded to both players in the game at their respective hosts and ports,
        # with the expected event bytes.
        expected_calls = [
            call(self.TEST_EVENT_BYTES, (self.TEST_HOST, self.TEST_PORT)),
            call(self.TEST_EVENT_BYTES, (self.TEST_HOST_2, self.TEST_PORT_2))
        ]
        self.assertEqual(expected_calls, self.mock_socket.sendto.mock_calls)

        self.mock_socket.reset_mock()

        # However, if we forward it again with a gate this time, we expect nothing to be sent, since the gate prevents
        # the packet from being forwarded.
        self.request_handler._forward_packet(self.TEST_EVENT, self.TEST_GAME_NAME, self.mock_socket,
                                             gate=lambda pd: False)
        self.mock_socket.sendto.assert_not_called()

    def test_process_event(self):
        """
        Ensure that events are correctly assigned to the correct process method based on their type.
        """

        def validate_event_type(event: Event, expected_method: str, with_sock: bool = True):
            """
            Ensure that the given event, when processed, calls the expected process method.
            :param event: The event to process and validate.
            :param expected_method: The name of the method we expect to be called in the request handler when processing
                                    the given event.
            :param with_sock: Whether we expect the socket to be included as an argument in the call to the expected
                              method.
            """
            # Mock out the method.
            setattr(self.request_handler, expected_method, MagicMock())
            self.request_handler.process_event(event, self.mock_socket)
            expected_args: list = [event, self.mock_socket] if with_sock else [event]
            # Ensure the method was called with the expected arguments.
            getattr(self.request_handler, expected_method).assert_called_with(*expected_args)

        # Go through each event type.
        validate_event_type(CreateEvent(EventType.CREATE, self.TEST_IDENTIFIER, self.TEST_GAME_CONFIG),
                            "process_create_event")
        validate_event_type(InitEvent(EventType.INIT, self.TEST_IDENTIFIER, self.TEST_GAME_NAME), "process_init_event")
        validate_event_type(UpdateEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.FOUND_SETTLEMENT,
                                        self.TEST_GAME_NAME, Faction.AGRICULTURISTS), "process_update_event")
        validate_event_type(QueryEvent(EventType.QUERY, self.TEST_IDENTIFIER), "process_query_event")
        validate_event_type(LeaveEvent(EventType.LEAVE, self.TEST_IDENTIFIER, self.TEST_GAME_NAME),
                            "process_leave_event")
        validate_event_type(JoinEvent(EventType.JOIN, self.TEST_IDENTIFIER,
                                      self.TEST_GAME_NAME, Faction.AGRICULTURISTS), "process_join_event")
        validate_event_type(RegisterEvent(EventType.REGISTER, self.TEST_IDENTIFIER, self.TEST_PORT),
                            "process_register_event")
        validate_event_type(EndTurnEvent(EventType.END_TURN, self.TEST_IDENTIFIER, self.TEST_GAME_NAME),
                            "process_end_turn_event")
        validate_event_type(UnreadyEvent(EventType.UNREADY, self.TEST_IDENTIFIER, self.TEST_GAME_NAME),
                            "process_unready_event", with_sock=False)
        validate_event_type(AutofillEvent(EventType.AUTOFILL, self.TEST_IDENTIFIER, self.TEST_GAME_NAME),
                            "process_autofill_event")
        validate_event_type(SaveEvent(EventType.SAVE, self.TEST_IDENTIFIER, self.TEST_GAME_NAME),
                            "process_save_event", with_sock=False)
        validate_event_type(QuerySavesEvent(EventType.QUERY_SAVES, self.TEST_IDENTIFIER), "process_query_saves_event")
        validate_event_type(LoadEvent(EventType.LOAD, self.TEST_IDENTIFIER, "Save 1"), "process_load_event")
        validate_event_type(Event(EventType.KEEPALIVE, self.TEST_IDENTIFIER),
                            "process_keepalive_event", with_sock=False)

    @patch("random.choice")
    def test_process_create_event_server(self, random_choice_mock: MagicMock):
        """
        Ensure that the game server correctly processes create events.
        """
        test_event: CreateEvent = CreateEvent(EventType.CREATE, self.TEST_IDENTIFIER, self.TEST_GAME_CONFIG)
        test_faction: Faction = test_event.cfg.player_faction
        taken_lobby_name: str = LOBBY_NAMES[0]
        test_lobby_name: str = LOBBY_NAMES[1]
        test_player_name: str = PLAYER_NAMES[0]
        self.mock_server.is_server = True
        # Add in an extra game state so we can see the lobby name iteration process.
        self.mock_server.game_states_ref = {taken_lobby_name: GameState()}
        # There are two different calls to random.choice() when processing create events as the server. Firstly, the
        # lobby name is chosen, and subsequently the player's name is chosen. We mock the method to initially return a
        # lobby name that's already been taken, thus covering the case where another lobby name needs to be randomly
        # selected. Our second return value is a valid lobby name, and we finally return a player name.
        random_choice_mock.side_effect = [taken_lobby_name, test_lobby_name, test_player_name]

        # Process our test event.
        self.request_handler.process_create_event(test_event, self.mock_socket)

        # The game state should have been created, with the expected Player object.
        self.assertIn(test_lobby_name, self.mock_server.game_states_ref)
        self.assertListEqual([Player(test_player_name, test_faction, FACTION_COLOURS[test_faction])],
                             self.mock_server.game_states_ref[test_lobby_name].players)
        # A Namer and MoveMaker should have been created for the lobby.
        self.assertIn(test_lobby_name, self.mock_server.namers_ref)
        self.assertIn(test_lobby_name, self.mock_server.move_makers_ref)
        # The player's identifier should have been added to the game clients for this lobby.
        self.assertIn(test_lobby_name, self.mock_server.game_clients_ref)
        self.assertListEqual([PlayerDetails(test_player_name, test_faction, test_event.identifier)],
                             self.mock_server.game_clients_ref[test_lobby_name])
        # The game's config should have been saved under the lobby name.
        self.assertIn(test_lobby_name, self.mock_server.lobbies_ref)
        self.assertEqual(test_event.cfg, self.mock_server.lobbies_ref[test_lobby_name])
        # We also expect the event itself to have been added to, with the additional information required for the client
        # to handle the response.
        self.assertEqual(test_lobby_name, test_event.lobby_name)
        self.assertEqual(self.mock_server.game_clients_ref[test_lobby_name], test_event.player_details)
        # Lastly, we expect the server to have sent a packet containing a JSON representation of the event to the client
        # that originally dispatched the create event.
        self.mock_socket.sendto.assert_called_with(json.dumps(test_event, cls=SaveEncoder).encode(),
                                                   (self.TEST_HOST, self.TEST_PORT))

    def test_process_create_event_client(self):
        """
        Ensure that game clients correctly process responses to create events.
        """
        test_name: str = PLAYER_NAMES[0]
        test_faction: Faction = Faction.AGRICULTURISTS
        test_event: CreateEvent = \
            CreateEvent(EventType.CREATE, self.TEST_IDENTIFIER, self.TEST_GAME_CONFIG,
                        # Since this is a response event from the game server, it has the generated lobby name and
                        # player details as well.
                        lobby_name=self.TEST_GAME_NAME,
                        player_details=[PlayerDetails(test_name, test_faction, self.TEST_IDENTIFIER)])
        self.mock_server.is_server = False
        # Create a local game state for the client.
        self.mock_server.game_states_ref["local"] = GameState()
        gs: GameState = self.mock_server.game_states_ref["local"]
        gc: GameController = self.mock_server.game_controller_ref
        gc.namer.reset = MagicMock()

        # The game state is not initialised to begin with.
        self.assertFalse(gs.players)
        self.assertEqual(0, gs.player_idx)
        self.assertFalse(gs.located_player_idx)
        # The client should also have no multiplayer lobby.
        self.assertIsNone(gc.menu.multiplayer_lobby)

        # Process our test event.
        self.request_handler.process_event(test_event, self.mock_socket)

        # The local game state should now have a player with the appropriate name, faction, and colour.
        self.assertEqual(1, len(gs.players))
        self.assertEqual(test_name, gs.players[0].name)
        self.assertEqual(test_faction, gs.players[0].faction)
        self.assertEqual(FACTION_COLOURS[test_faction], gs.players[0].colour)
        # The player's index should also have been located.
        self.assertEqual(0, gs.player_idx)
        self.assertTrue(gs.located_player_idx)
        # The client's multiplayer lobby should also have been initialised.
        self.assertEqual(test_event.lobby_name, gc.menu.multiplayer_lobby.name)
        self.assertEqual(test_event.player_details, gc.menu.multiplayer_lobby.current_players)
        self.assertEqual(test_event.cfg, gc.menu.multiplayer_lobby.cfg)
        self.assertIsNone(gc.menu.multiplayer_lobby.current_turn)
        gc.namer.reset.assert_called()

    @patch("random.seed")
    def test_process_init_event_server(self, random_seed_mock: MagicMock):
        """
        Ensure that the game server correctly processes init events.
        """
        test_event: InitEvent = InitEvent(EventType.INIT, self.TEST_IDENTIFIER, self.TEST_GAME_NAME)
        self.mock_server.is_server = True
        gs: GameState = self.TEST_GAME_STATE
        # Add an AI player so we can see how its initialised settlement details are forwarded to the clients.
        ai_player: Player = Player("Mr. Roboto", Faction.FUNDAMENTALISTS, 2,
                                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL))
        gs.players.append(ai_player)
        # Initialise some game state variables to mostly nonsensical values - all that matters is that these are
        # appropriately changed.
        gs.turn = 2
        gs.until_night = 0
        gs.nighttime_left = 1
        # Pass the necessary references down to the server.
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = gs
        test_namer: Namer = Namer()
        self.mock_server.namers_ref[self.TEST_GAME_NAME] = test_namer
        test_move_maker: MoveMaker = MoveMaker(test_namer)
        self.mock_server.move_makers_ref[self.TEST_GAME_NAME] = test_move_maker

        # As a fresh game state, initially the game should not be started and the board should be None, as should its
        # reference in the MoveMaker.
        self.assertFalse(gs.game_started)
        self.assertIsNone(gs.board)
        self.assertIsNone(test_move_maker.board_ref)

        # Process our test event.
        self.request_handler.process_init_event(test_event, self.mock_socket)

        # The game state should have been initialised in the standard fashion.
        self.assertTrue(gs.game_started)
        self.assertEqual(1, gs.turn)
        random_seed_mock.assert_called()
        self.assertTrue(10 <= gs.until_night <= 20)
        self.assertFalse(gs.nighttime_left)
        self.assertFalse(gs.on_menu)
        self.assertIsNotNone(gs.board)
        self.assertEqual(gs.board, test_move_maker.board_ref)
        # We expect each client to have been notified of the location of the AI player's settlement.
        ai_update_settlement_packets = \
            [c for c in self.mock_socket.sendto.mock_calls if json.loads(c.args[0])["type"] == EventType.UPDATE]
        self.assertEqual(2, len(ai_update_settlement_packets))
        # We also expect each client to have been sent the quad details for the board. The board has 9000 quads and each
        # packet has 100 quads. As such, we expect 90 packets to have been sent to each client.
        quad_init_packets = \
            [c for c in self.mock_socket.sendto.mock_calls if json.loads(c.args[0])["type"] == EventType.INIT]
        self.assertEqual(180, len(quad_init_packets))

    @patch.object(Overlay, "toggle_tutorial")
    @patch("source.networking.event_listener.save_stats_achievements")
    @patch("pyxel.mouse")
    def test_process_init_event_client(self,
                                       pyxel_mouse_mock: MagicMock,
                                       achievements_mock: MagicMock,
                                       overlay_toggle_tutorial_mock: MagicMock):
        """
        Ensure that game clients correctly process init events.
        """
        # The quad chunk we use for this test is just the same test quad over and over.
        test_quads_str: str = (minify_quad(self.TEST_QUAD) + ",") * 100
        # The test event will just be for the first quad chunk to begin with.
        test_event: InitEvent = InitEvent(EventType.INIT, self.TEST_IDENTIFIER, self.TEST_GAME_NAME,
                                          until_night=1, cfg=self.TEST_GAME_CONFIG,
                                          quad_chunk=test_quads_str, quad_chunk_idx=0)
        self.mock_server.is_server = False
        gs: GameState = self.TEST_GAME_STATE
        # Manually change the until night value in game state so we can be sure that it was set from the received
        # packet, and didn't just happen to be randomly the same as the event.
        gs.until_night = 0
        self.mock_server.game_states_ref["local"] = gs
        gc: GameController = self.TEST_GAME_CONTROLLER
        # Set an initial last turn time so we can see it being updated later.
        initial_last_turn_time: float = 0
        gc.last_turn_time = initial_last_turn_time
        gc.music_player.stop_menu_music = MagicMock()
        gc.music_player.play_game_music = MagicMock()

        # Until the first packet is processed, the game state should have no board.
        self.assertIsNone(gs.board)
        self.assertIsNone(gc.move_maker.board_ref)

        # Process our test event.
        self.request_handler.process_init_event(test_event, self.mock_socket)

        # The until night value in game state should now be the same as the event.
        self.assertEqual(test_event.until_night, gs.until_night)
        # The game state should also now have a board, populated with the game config and name from the event.
        self.assertIsNotNone(gs.board)
        self.assertEqual(test_event.cfg, gs.board.game_config)
        self.assertEqual(test_event.game_name, gs.board.game_name)
        self.assertEqual(gc.move_maker.board_ref, gs.board)
        # However, since we have only simulated the client receiving a single quad chunk, we do not expect any of the
        # game-entering logic to have occurred. As such, the client should still be on the menu.
        pyxel_mouse_mock.assert_not_called()
        self.assertEqual(initial_last_turn_time, gc.last_turn_time)
        self.assertFalse(gs.game_started)
        self.assertTrue(gs.on_menu)
        achievements_mock.assert_not_called()
        overlay_toggle_tutorial_mock.assert_not_called()
        self.assertFalse(gs.board.overlay.total_settlement_count)
        gc.music_player.stop_menu_music.assert_not_called()
        gc.music_player.play_game_music.assert_not_called()

        # Simulate the client receiving the rest of the quad chunks. It doesn't make for a great board, but
        # for testing purposes, it doesn't matter that every quad will be the same.
        for i in range(1, 90):
            test_event.quad_chunk_idx = i
            self.request_handler.process_init_event(test_event, self.mock_socket)

        # Prior to entering the game, we expect the quad for each generated settlement to have been linked to the quads
        # on the actual board, rather than just being a deep copy.
        for p in gs.players:
            for s in p.settlements:
                self.assertIs(s.quads[0], gs.board.quads[s.location[1]][s.location[0]])
        # Since the board has now been fully populated with quads, we expect the client to have entered the game.
        pyxel_mouse_mock.assert_called_with(visible=True)
        self.assertGreater(gc.last_turn_time, initial_last_turn_time)
        self.assertTrue(gs.game_started)
        self.assertFalse(gs.on_menu)
        achievements_mock.assert_called_with(gs, faction_to_add=gs.players[gs.player_idx].faction)
        overlay_toggle_tutorial_mock.assert_called()
        # You would normally think that this would be 2, since there are two settlements in the game. However, because
        # this is an init event - meaning that the game has just started - we take into account that the client is about
        # to found their first settlement.
        self.assertEqual(3, gs.board.overlay.total_settlement_count)
        gc.music_player.stop_menu_music.assert_called()
        gc.music_player.play_game_music.assert_called()
        # We can even make sure that the correct quad was assigned for all of the board's quads.
        for i in range(90):
            for j in range(100):
                # We do have to mock the location however, as that was the same in the quad chunk.
                self.TEST_QUAD.location = j, i
                self.assertEqual(self.TEST_QUAD, gs.board.quads[i][j])

    def test_process_update_event(self):
        """
        Ensure that updated events are correctly assigned to the correct process method based on their action.
        """

        def validate_update_event_action(event: UpdateEvent, expected_method: str):
            """
            Ensure that the given update event, when processed, calls the expected process method.
            :param event: The update event to process and validate.
            :param expected_method: The name of the method we expect to be called in the request handler when processing
                                    the given update event.
            """
            # Mock out the method.
            setattr(self.request_handler, expected_method, MagicMock())
            self.request_handler.process_update_event(event, self.mock_socket)
            # Ensure the method was called with the expected arguments.
            getattr(self.request_handler, expected_method).assert_called_with(event, self.mock_socket)

        # Go through each update event action.
        validate_update_event_action(FoundSettlementEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                          UpdateAction.FOUND_SETTLEMENT, self.TEST_GAME_NAME,
                                                          Faction.AGRICULTURISTS, self.TEST_SETTLEMENT),
                                     "process_found_settlement_event")
        validate_update_event_action(SetBlessingEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.SET_BLESSING,
                                                      self.TEST_GAME_NAME, Faction.AGRICULTURISTS,
                                                      OngoingBlessing(BLESSINGS["beg_spl"])),
                                     "process_set_blessing_event")
        validate_update_event_action(SetConstructionEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                          UpdateAction.SET_CONSTRUCTION, self.TEST_GAME_NAME,
                                                          Faction.AGRICULTURISTS, ResourceCollection(), "Cool",
                                                          Construction(PROJECTS[0])),
                                     "process_set_construction_event")
        validate_update_event_action(MoveUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.MOVE_UNIT,
                                                   self.TEST_GAME_NAME, Faction.AGRICULTURISTS, (1, 1), (2, 2), 0,
                                                   False),
                                     "process_move_unit_event")
        validate_update_event_action(DeployUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.DEPLOY_UNIT,
                                                     self.TEST_GAME_NAME, Faction.AGRICULTURISTS, "Cool", (3, 3)),
                                     "process_deploy_unit_event")
        validate_update_event_action(GarrisonUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                       UpdateAction.GARRISON_UNIT, self.TEST_GAME_NAME,
                                                       Faction.AGRICULTURISTS, (4, 4), 1, "Cool"),
                                     "process_garrison_unit_event")
        validate_update_event_action(InvestigateEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.INVESTIGATE,
                                                      self.TEST_GAME_NAME, Faction.AGRICULTURISTS, (5, 5), (5, 6),
                                                      InvestigationResult.POWER),
                                     "process_investigate_event")
        validate_update_event_action(BesiegeSettlementEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                            UpdateAction.BESIEGE_SETTLEMENT, self.TEST_GAME_NAME,
                                                            Faction.AGRICULTURISTS, (6, 6), "Cool"),
                                     "process_besiege_settlement_event")
        validate_update_event_action(BuyoutConstructionEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                             UpdateAction.BUYOUT_CONSTRUCTION, self.TEST_GAME_NAME,
                                                             Faction.AGRICULTURISTS, "Cool", 3.50),
                                     "process_buyout_construction_event")
        validate_update_event_action(DisbandUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.DISBAND_UNIT,
                                                      self.TEST_GAME_NAME, Faction.AGRICULTURISTS, (7, 7)),
                                     "process_disband_unit_event")
        validate_update_event_action(AttackUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.ATTACK_UNIT,
                                                     self.TEST_GAME_NAME, Faction.AGRICULTURISTS, (8, 8), (8, 9)),
                                     "process_attack_unit_event")
        validate_update_event_action(AttackSettlementEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                           UpdateAction.ATTACK_SETTLEMENT, self.TEST_GAME_NAME,
                                                           Faction.AGRICULTURISTS, (9, 9), "Cool"),
                                     "process_attack_settlement_event")
        validate_update_event_action(HealUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.HEAL_UNIT,
                                                   self.TEST_GAME_NAME, Faction.AGRICULTURISTS, (10, 10), (10, 11)),
                                     "process_heal_unit_event")
        validate_update_event_action(BoardDeployerEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                        UpdateAction.BOARD_DEPLOYER, self.TEST_GAME_NAME,
                                                        Faction.AGRICULTURISTS, (11, 11), (11, 12), 1),
                                     "process_board_deployer_event")
        validate_update_event_action(DeployerDeployEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                         UpdateAction.DEPLOYER_DEPLOY, self.TEST_GAME_NAME,
                                                         Faction.AGRICULTURISTS, (12, 12), 1, (12, 13)),
                                     "process_deployer_deploy_event")

    def test_process_found_settlement_event_server(self):
        """
        Ensure that the game server correctly processes found settlement events.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        player.units.append(self.TEST_SETTLER_UNIT)
        settler: Unit = player.units[1]
        quad: Quad = Quad(Biome.DESERT, 0, 0, 0, 0, settler.location)
        # Chuck a unit in the garrison so we can make sure the unit migration works as well.
        new_setl: Settlement = Settlement("New One", settler.location, [], [quad], ResourceCollection(),
                                          garrison=[self.TEST_HEALER_UNIT])
        test_event: FoundSettlementEvent = FoundSettlementEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                                UpdateAction.FOUND_SETTLEMENT, self.TEST_GAME_NAME,
                                                                player.faction, new_setl, from_settler=True)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE
        namer: Namer = Namer()
        namer.remove_settlement_name = MagicMock()
        self.mock_server.namers_ref[self.TEST_GAME_NAME] = namer

        # The player should only have the one settlement to begin with.
        self.assertListEqual([self.TEST_SETTLEMENT], player.settlements)
        # They should also have no seen quads.
        self.assertFalse(player.quads_seen)
        # The player should lastly have two deployed units, one of which is the settler that will found the settlement.
        self.assertListEqual([self.TEST_UNIT, settler], player.units)

        # Process our test event.
        self.request_handler.process_found_settlement_event(test_event, self.mock_socket)

        # The player should now have a new settlement in accordance with the event, as well as some seen quads.
        self.assertListEqual([self.TEST_SETTLEMENT, new_setl], player.settlements)
        self.assertTrue(player.quads_seen)
        # We also expect the settler unit to no longer exist.
        self.assertListEqual([self.TEST_UNIT], player.units)
        # The game server should also have removed the settlement's name from the game's Namer so that future AI
        # settlements do not have the chance of name collisions occurring.
        namer.remove_settlement_name.assert_called_with(new_setl.name, quad.biome)
        # Lastly, this information should have been forwarded by the server just once to the other player.
        self.mock_socket.sendto.assert_called_once()

    def test_process_found_settlement_event_client(self):
        """
        Ensure that game clients correctly process found settlement events.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        player.units.append(self.TEST_SETTLER_UNIT)
        settler: Unit = player.units[1]
        quad: Quad = Quad(Biome.DESERT, 0, 0, 0, 0, settler.location)
        # Chuck a unit in the garrison so we can make sure the unit migration works as well.
        new_setl: Settlement = Settlement("New One", settler.location, [], [quad], ResourceCollection(),
                                          garrison=[self.TEST_HEALER_UNIT])
        test_event: FoundSettlementEvent = FoundSettlementEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                                UpdateAction.FOUND_SETTLEMENT, self.TEST_GAME_NAME,
                                                                player.faction, new_setl, from_settler=True)
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE
        self.mock_server.game_controller_ref.namer.remove_settlement_name = MagicMock()

        # The player should only have the one settlement to begin with.
        self.assertListEqual([self.TEST_SETTLEMENT], player.settlements)
        # They should also have no seen quads.
        self.assertFalse(player.quads_seen)
        # The player should lastly have two deployed units, one of which is the settler that will found the settlement.
        self.assertListEqual([self.TEST_UNIT, settler], player.units)

        # Process our test event.
        self.request_handler.process_found_settlement_event(test_event, self.mock_socket)

        # The player should now have a new settlement in accordance with the event, as well as some seen quads.
        self.assertListEqual([self.TEST_SETTLEMENT, new_setl], player.settlements)
        self.assertTrue(player.quads_seen)
        # We also expect the settler unit to no longer exist.
        self.assertListEqual([self.TEST_UNIT], player.units)
        # The client should also have removed the settlement's name from their Namer so that future settlements do not
        # have the chance of name collisions occurring.
        self.mock_server.game_controller_ref.namer.remove_settlement_name.assert_called_with(new_setl.name, quad.biome)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

    def test_process_set_blessing_event_server(self):
        """
        Ensure that the game server correctly processes set blessing events.
        """
        test_event: SetBlessingEvent = SetBlessingEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                        UpdateAction.SET_BLESSING, self.TEST_GAME_NAME,
                                                        Faction.AGRICULTURISTS, OngoingBlessing(BLESSINGS["beg_spl"]))
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE

        # The player with the same faction as the event should have no ongoing blessing to begin with.
        self.assertIsNone(self.TEST_GAME_STATE.players[0].ongoing_blessing)

        # Process our test event.
        self.request_handler.process_set_blessing_event(test_event, self.mock_socket)

        # The player should now have the same ongoing blessing as the event, and this information should have been
        # forwarded just the once, to the other player in the game.
        self.assertEqual(test_event.blessing, self.TEST_GAME_STATE.players[0].ongoing_blessing)
        self.mock_socket.sendto.assert_called_once()

    def test_process_set_blessing_event_client(self):
        """
        Ensure that game clients correctly process forwarded set blessing event packets.
        """
        test_event: SetBlessingEvent = SetBlessingEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                        UpdateAction.SET_BLESSING, self.TEST_GAME_NAME,
                                                        Faction.AGRICULTURISTS, OngoingBlessing(BLESSINGS["beg_spl"]))
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # The player with the same faction as the event should have no ongoing blessing to begin with.
        self.assertIsNone(self.TEST_GAME_STATE.players[0].ongoing_blessing)

        # Process our test event.
        self.request_handler.process_set_blessing_event(test_event, self.mock_socket)

        # The player should now have the same ongoing blessing as the event, and this information should not have been
        # forwarded, since this is a client.
        self.assertEqual(test_event.blessing, self.TEST_GAME_STATE.players[0].ongoing_blessing)
        self.mock_socket.sendto.assert_not_called()

    def test_process_set_construction_event_server(self):
        """
        Ensure that the game server correctly processes set construction events.
        """
        test_event: SetConstructionEvent = SetConstructionEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                                UpdateAction.SET_CONSTRUCTION, self.TEST_GAME_NAME,
                                                                Faction.AGRICULTURISTS, ResourceCollection(magma=1),
                                                                self.TEST_SETTLEMENT.name,
                                                                # Initially, construct an improvement.
                                                                Construction(IMPROVEMENTS[0]))
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE
        player: Player = self.TEST_GAME_STATE.players[0]

        self.assertFalse(player.resources)
        # The settlement should have no current work to begin with.
        self.assertIsNone(player.settlements[0].current_work)

        # Process our test event.
        self.request_handler.process_set_construction_event(test_event, self.mock_socket)

        # This is not a realistic use case, since you can't gain resources by constructing something, but it serves to
        # show that the player's resources are updated to be the same as the event's.
        self.assertEqual(test_event.player_resources, player.resources)
        # The settlement should also have had its construction updated.
        self.assertEqual(test_event.construction, player.settlements[0].current_work)
        # Lastly, this information should have been forwarded by the server just once to the other player.
        self.mock_socket.sendto.assert_called_once()

        # Make sure the same construction logic works for projects.
        test_event.construction = Construction(PROJECTS[0])
        self.request_handler.process_set_construction_event(test_event, self.mock_socket)
        self.assertEqual(test_event.construction, player.settlements[0].current_work)

        # Make sure the same construction logic works for units.
        test_event.construction = Construction(UNIT_PLANS[0])
        self.request_handler.process_set_construction_event(test_event, self.mock_socket)
        self.assertEqual(test_event.construction, player.settlements[0].current_work)

    def test_process_set_construction_event_client(self):
        """
        Ensure that game clients correctly process forwarded set construction event packets.
        """
        test_event: SetConstructionEvent = SetConstructionEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                                UpdateAction.SET_CONSTRUCTION, self.TEST_GAME_NAME,
                                                                Faction.AGRICULTURISTS, ResourceCollection(magma=1),
                                                                self.TEST_SETTLEMENT.name,
                                                                # Initially, construct an improvement.
                                                                Construction(IMPROVEMENTS[0]))
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE
        player: Player = self.TEST_GAME_STATE.players[0]

        self.assertFalse(player.resources)
        # The settlement should have no current work to begin with.
        self.assertIsNone(player.settlements[0].current_work)

        # Process our test event.
        self.request_handler.process_set_construction_event(test_event, self.mock_socket)

        # This is not a realistic use case, since you can't gain resources by constructing something, but it serves to
        # show that the player's resources are updated to be the same as the event's.
        self.assertEqual(test_event.player_resources, player.resources)
        # The settlement should also have had its construction updated.
        self.assertEqual(test_event.construction, player.settlements[0].current_work)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

        # Make sure the same construction logic works for projects.
        test_event.construction = Construction(PROJECTS[0])
        self.request_handler.process_set_construction_event(test_event, self.mock_socket)
        self.assertEqual(test_event.construction, player.settlements[0].current_work)

        # Make sure the same construction logic works for units.
        test_event.construction = Construction(UNIT_PLANS[0])
        self.request_handler.process_set_construction_event(test_event, self.mock_socket)
        self.assertEqual(test_event.construction, player.settlements[0].current_work)

    def test_process_move_unit_event_server(self):
        """
        Ensure that the game server correctly processes move unit events.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        unit: Unit = player.units[0]
        test_event: MoveUnitEvent = MoveUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.MOVE_UNIT,
                                                  self.TEST_GAME_NAME, player.faction, unit.location, (6, 6), 0, True)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE

        # The player should have no seen quads to begin with. We could also assert on the unit's attributes, but since
        # we control that anyway, there's no point.
        self.assertFalse(player.quads_seen)

        # Process our test event.
        self.request_handler.process_move_unit_event(test_event, self.mock_socket)

        # The unit's location, stamina, and besieging attributes should have been updated accordingly.
        self.assertTupleEqual(test_event.new_loc, unit.location)
        self.assertEqual(test_event.new_stamina, unit.remaining_stamina)
        self.assertEqual(test_event.besieging, unit.besieging)
        # The player should now also have some seen quads.
        self.assertTrue(player.quads_seen)
        # Lastly, this information should have been forwarded by the server just once to the other player.
        self.mock_socket.sendto.assert_called_once()

    def test_process_move_unit_event_client(self):
        """
        Ensure that game clients correctly process forwarded move unit event packets.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        unit: Unit = player.units[0]
        test_event: MoveUnitEvent = MoveUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.MOVE_UNIT,
                                                  self.TEST_GAME_NAME, player.faction, unit.location, (6, 6), 0, True)
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # The player should have no seen quads to begin with. We could also assert on the unit's attributes, but since
        # we control that anyway, there's no point.
        self.assertFalse(player.quads_seen)

        # Process our test event.
        self.request_handler.process_move_unit_event(test_event, self.mock_socket)

        # The unit's location, stamina, and besieging attributes should have been updated accordingly.
        self.assertTupleEqual(test_event.new_loc, unit.location)
        self.assertEqual(test_event.new_stamina, unit.remaining_stamina)
        self.assertEqual(test_event.besieging, unit.besieging)
        # The player should now also have some seen quads.
        self.assertTrue(player.quads_seen)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

    def test_process_deploy_unit_event_server(self):
        """
        Ensure that the game server correctly processes deploy unit events.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        # Garrison the test unit in the test settlement.
        unit: Unit = player.units.pop()
        setl: Settlement = player.settlements[0]
        setl.garrison = [unit]
        unit.garrisoned = True
        test_event: DeployUnitEvent = DeployUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.DEPLOY_UNIT,
                                                      self.TEST_GAME_NAME, player.faction, setl.name, (7, 7))
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE

        # The player should have no seen quads or deployed units initially.
        self.assertFalse(player.quads_seen)
        self.assertFalse(player.units)

        # Process our test event.
        self.request_handler.process_deploy_unit_event(test_event, self.mock_socket)

        # The settlement's garrison should now be empty, with the unit deployed at the location given by the event.
        self.assertFalse(setl.garrison)
        self.assertFalse(unit.garrisoned)
        self.assertTupleEqual(test_event.location, unit.location)
        # The player should also now have some seen quads, and a deployed unit.
        self.assertTrue(player.quads_seen)
        self.assertTrue(player.units)
        # Lastly, this information should have been forwarded by the server just once to the other player.
        self.mock_socket.sendto.assert_called_once()

    def test_process_deploy_unit_event_client(self):
        """
        Ensure that game clients correctly process forwarded deploy unit event packets.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        # Garrison the test unit in the test settlement.
        unit: Unit = player.units.pop()
        setl: Settlement = player.settlements[0]
        setl.garrison = [unit]
        unit.garrisoned = True
        test_event: DeployUnitEvent = DeployUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.DEPLOY_UNIT,
                                                      self.TEST_GAME_NAME, player.faction, setl.name, (7, 7))
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # The player should have no seen quads or deployed units initially.
        self.assertFalse(player.quads_seen)
        self.assertFalse(player.units)

        # Process our test event.
        self.request_handler.process_deploy_unit_event(test_event, self.mock_socket)

        # The settlement's garrison should now be empty, with the unit deployed at the location given by the event.
        self.assertFalse(setl.garrison)
        self.assertFalse(unit.garrisoned)
        self.assertTupleEqual(test_event.location, unit.location)
        # The player should also now have some seen quads, and a deployed unit.
        self.assertTrue(player.quads_seen)
        self.assertTrue(player.units)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

    def test_process_garrison_unit_event_server(self):
        """
        Ensure that the game server correctly processes garrison unit events.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        unit: Unit = player.units[0]
        setl: Settlement = player.settlements[0]
        test_event: GarrisonUnitEvent = GarrisonUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                          UpdateAction.GARRISON_UNIT, self.TEST_GAME_NAME,
                                                          player.faction, unit.location, 1, setl.name)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE

        # The unit should be deployed and the settlement's garrison should be empty to begin with.
        self.assertFalse(unit.garrisoned)
        self.assertFalse(setl.garrison)
        self.assertTrue(player.units)

        # Process our test event.
        self.request_handler.process_garrison_unit_event(test_event, self.mock_socket)

        # The unit should have been garrisoned with reduced stamina according to the event.
        self.assertEqual(test_event.new_stamina, unit.remaining_stamina)
        self.assertTrue(unit.garrisoned)
        self.assertTrue(setl.garrison)
        # Naturally, this means the player no longer has any deployed units either.
        self.assertFalse(player.units)
        # Lastly, this information should have been forwarded by the server just once to the other player.
        self.mock_socket.sendto.assert_called_once()

    def test_process_garrison_unit_event_client(self):
        """
        Ensure that game clients correctly process garrison unit events.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        unit: Unit = player.units[0]
        setl: Settlement = player.settlements[0]
        test_event: GarrisonUnitEvent = GarrisonUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                          UpdateAction.GARRISON_UNIT, self.TEST_GAME_NAME,
                                                          player.faction, unit.location, 1, setl.name)
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # The unit should be deployed and the settlement's garrison should be empty to begin with.
        self.assertFalse(unit.garrisoned)
        self.assertFalse(setl.garrison)
        self.assertTrue(player.units)

        # Process our test event.
        self.request_handler.process_garrison_unit_event(test_event, self.mock_socket)

        # The unit should have been garrisoned with reduced stamina according to the event.
        self.assertEqual(test_event.new_stamina, unit.remaining_stamina)
        self.assertTrue(unit.garrisoned)
        self.assertTrue(setl.garrison)
        # Naturally, this means the player no longer has any deployed units either.
        self.assertFalse(player.units)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

    def test_process_investigate_event_server(self):
        """
        Ensure that the game server correctly processes investigate events.
        """
        # For this test, we actually need an initialised board with quads.
        self.TEST_GAME_STATE.board = Board(self.TEST_GAME_CONFIG, Namer(), {})
        self.TEST_GAME_STATE.board.generate_quads(True, True)
        player: Player = self.TEST_GAME_STATE.players[0]
        # Give the player a blessing so that we can see it progress with the fortune investigation result.
        player.ongoing_blessing = OngoingBlessing(BLESSINGS["beg_spl"])
        unit: Unit = player.units[0]
        # Pick a quad for our relic.
        relic_loc: Tuple[int, int] = 11, 12
        relic_quad: Quad = self.TEST_GAME_STATE.board.quads[relic_loc[1]][relic_loc[0]]
        test_event: InvestigateEvent = InvestigateEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                        UpdateAction.INVESTIGATE, self.TEST_GAME_NAME, player.faction,
                                                        unit.location, relic_loc, InvestigationResult.NONE)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE

        relic_quad.is_relic = True
        # Testing the fortune investigation result.
        test_event.result = InvestigationResult.FORTUNE
        self.assertFalse(player.ongoing_blessing.fortune_consumed)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect some progress to have been made on the player's ongoing blessing.
        self.assertTrue(player.ongoing_blessing.fortune_consumed)
        # We also expect the quad to no longer have a relic.
        self.assertFalse(relic_quad.is_relic)
        # Lastly, this information should have been forwarded by the server just once to the other player.
        self.mock_socket.sendto.assert_called_once()

        # Reset the mock state.
        relic_quad.is_relic = True
        self.mock_socket.reset_mock()
        # Testing the wealth investigation result.
        test_event.result = InvestigationResult.WEALTH
        self.assertFalse(player.wealth)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the player to now have some wealth.
        self.assertTrue(player.wealth)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_called_once()

        relic_quad.is_relic = True
        self.mock_socket.reset_mock()
        # Testing the vision investigation result.
        test_event.result = InvestigationResult.VISION
        self.assertFalse(player.quads_seen)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the player to now have some seen quads.
        self.assertTrue(player.quads_seen)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_called_once()

        relic_quad.is_relic = True
        self.mock_socket.reset_mock()
        # Testing the health investigation result.
        test_event.result = InvestigationResult.HEALTH
        self.assertEqual(100, unit.plan.max_health)
        self.assertEqual(50, unit.health)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the unit's current and max health to both have been increased by five.
        self.assertEqual(105, unit.plan.max_health)
        self.assertEqual(55, unit.health)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_called_once()

        relic_quad.is_relic = True
        self.mock_socket.reset_mock()
        # Testing the power investigation result.
        test_event.result = InvestigationResult.POWER
        self.assertEqual(100, unit.plan.power)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the unit's power to have been increased by five.
        self.assertEqual(105, unit.plan.power)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_called_once()

        relic_quad.is_relic = True
        self.mock_socket.reset_mock()
        # Testing the stamina investigation result.
        test_event.result = InvestigationResult.STAMINA
        self.assertEqual(3, unit.plan.total_stamina)
        self.assertEqual(2, unit.remaining_stamina)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the unit's total stamina to have been increased, and its current stamina to have been replenished.
        self.assertEqual(4, unit.plan.total_stamina)
        self.assertEqual(4, unit.remaining_stamina)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_called_once()

        relic_quad.is_relic = True
        self.mock_socket.reset_mock()
        # Testing the upkeep investigation result.
        test_event.result = InvestigationResult.UPKEEP
        self.assertEqual(25, unit.plan.cost)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the unit to no longer have any upkeep, which is derived from its cost.
        self.assertFalse(unit.plan.cost)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_called_once()

        relic_quad.is_relic = True
        self.mock_socket.reset_mock()
        # Testing the ore investigation result.
        test_event.result = InvestigationResult.ORE
        self.assertFalse(player.resources.ore)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the player to now have some ore.
        self.assertTrue(player.resources.ore)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_called_once()

        relic_quad.is_relic = True
        self.mock_socket.reset_mock()
        # Testing the timber investigation result.
        test_event.result = InvestigationResult.TIMBER
        self.assertFalse(player.resources.timber)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the player to now have some timber.
        self.assertTrue(player.resources.timber)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_called_once()

        relic_quad.is_relic = True
        self.mock_socket.reset_mock()
        # Testing the magma investigation result.
        test_event.result = InvestigationResult.MAGMA
        self.assertFalse(player.resources.magma)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the player to now have some magma.
        self.assertTrue(player.resources.magma)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_called_once()

        relic_quad.is_relic = True
        self.mock_socket.reset_mock()
        # Testing the failure/none investigation result.
        test_event.result = InvestigationResult.NONE
        # Copy the player and unit objects so that we can assert that they haven't changed.
        player_copy: Player = deepcopy(player)
        unit_copy: Unit = deepcopy(unit)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect no state changes to have occurred, since the investigation was not successful.
        self.assertEqual(player_copy, player)
        self.assertEqual(unit_copy, unit)
        self.mock_socket.sendto.assert_called_once()

    def test_process_investigate_event_client(self):
        """
        Ensure that game clients correctly process investigate events.
        """
        # For this test, we actually need an initialised board with quads.
        self.TEST_GAME_STATE.board = Board(self.TEST_GAME_CONFIG, Namer(), {})
        self.TEST_GAME_STATE.board.generate_quads(True, True)
        player: Player = self.TEST_GAME_STATE.players[0]
        # Give the player a blessing so that we can see it progress with the fortune investigation result.
        player.ongoing_blessing = OngoingBlessing(BLESSINGS["beg_spl"])
        unit: Unit = player.units[0]
        # Pick a quad for our relic.
        relic_loc: Tuple[int, int] = 11, 12
        relic_quad: Quad = self.TEST_GAME_STATE.board.quads[relic_loc[1]][relic_loc[0]]
        test_event: InvestigateEvent = InvestigateEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                        UpdateAction.INVESTIGATE, self.TEST_GAME_NAME, player.faction,
                                                        unit.location, relic_loc, InvestigationResult.NONE)
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        relic_quad.is_relic = True
        # Testing the fortune investigation result.
        test_event.result = InvestigationResult.FORTUNE
        self.assertFalse(player.ongoing_blessing.fortune_consumed)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect some progress to have been made on the player's ongoing blessing.
        self.assertTrue(player.ongoing_blessing.fortune_consumed)
        # We also expect the quad to no longer have a relic.
        self.assertFalse(relic_quad.is_relic)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

        relic_quad.is_relic = True
        # Testing the wealth investigation result.
        test_event.result = InvestigationResult.WEALTH
        self.assertFalse(player.wealth)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the player to now have some wealth.
        self.assertTrue(player.wealth)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_not_called()

        relic_quad.is_relic = True
        # Testing the vision investigation result.
        test_event.result = InvestigationResult.VISION
        self.assertFalse(player.quads_seen)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the player to now have some seen quads.
        self.assertTrue(player.quads_seen)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_not_called()

        relic_quad.is_relic = True
        # Testing the health investigation result.
        test_event.result = InvestigationResult.HEALTH
        self.assertEqual(100, unit.plan.max_health)
        self.assertEqual(50, unit.health)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the unit's current and max health to both have been increased by five.
        self.assertEqual(105, unit.plan.max_health)
        self.assertEqual(55, unit.health)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_not_called()

        relic_quad.is_relic = True
        # Testing the power investigation result.
        test_event.result = InvestigationResult.POWER
        self.assertEqual(100, unit.plan.power)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the unit's power to have been increased by five.
        self.assertEqual(105, unit.plan.power)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_not_called()

        relic_quad.is_relic = True
        # Testing the stamina investigation result.
        test_event.result = InvestigationResult.STAMINA
        self.assertEqual(3, unit.plan.total_stamina)
        self.assertEqual(2, unit.remaining_stamina)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the unit's total stamina to have been increased, and its current stamina to have been replenished.
        self.assertEqual(4, unit.plan.total_stamina)
        self.assertEqual(4, unit.remaining_stamina)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_not_called()

        relic_quad.is_relic = True
        # Testing the upkeep investigation result.
        test_event.result = InvestigationResult.UPKEEP
        self.assertEqual(25, unit.plan.cost)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the unit to no longer have any upkeep, which is derived from its cost.
        self.assertFalse(unit.plan.cost)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_not_called()

        relic_quad.is_relic = True
        # Testing the ore investigation result.
        test_event.result = InvestigationResult.ORE
        self.assertFalse(player.resources.ore)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the player to now have some ore.
        self.assertTrue(player.resources.ore)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_not_called()

        relic_quad.is_relic = True
        # Testing the timber investigation result.
        test_event.result = InvestigationResult.TIMBER
        self.assertFalse(player.resources.timber)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the player to now have some timber.
        self.assertTrue(player.resources.timber)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_not_called()

        relic_quad.is_relic = True
        # Testing the magma investigation result.
        test_event.result = InvestigationResult.MAGMA
        self.assertFalse(player.resources.magma)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect the player to now have some magma.
        self.assertTrue(player.resources.magma)
        self.assertFalse(relic_quad.is_relic)
        self.mock_socket.sendto.assert_not_called()

        relic_quad.is_relic = True
        # Testing the failure/none investigation result.
        test_event.result = InvestigationResult.NONE
        # Copy the player and unit objects so that we can assert that they haven't changed.
        player_copy: Player = deepcopy(player)
        unit_copy: Unit = deepcopy(unit)
        self.request_handler.process_investigate_event(test_event, self.mock_socket)
        # We expect no state changes to have occurred, since the investigation was not successful.
        self.assertEqual(player_copy, player)
        self.assertEqual(unit_copy, unit)
        self.mock_socket.sendto.assert_not_called()

    def test_process_besiege_settlement_event_server(self):
        """
        Ensure that the game server correctly processes besiege settlement events.
        """
        besieging_player: Player = self.TEST_GAME_STATE.players[0]
        besieged_player: Player = self.TEST_GAME_STATE.players[1]
        unit: Unit = besieging_player.units[0]
        setl: Settlement = besieged_player.settlements[0]
        test_event: BesiegeSettlementEvent = BesiegeSettlementEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                                    UpdateAction.BESIEGE_SETTLEMENT,
                                                                    self.TEST_GAME_NAME, besieging_player.faction,
                                                                    unit.location, setl.name)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE

        # Neither the unit nor the settlement should be in a siege situation.
        self.assertFalse(unit.besieging)
        self.assertFalse(setl.besieged)

        # Process our test event.
        self.request_handler.process_besiege_settlement_event(test_event, self.mock_socket)

        # The unit should now be laying siege to the settlement, with this information forwarded to the other player.
        self.assertTrue(unit.besieging)
        self.assertTrue(setl.besieged)
        self.mock_socket.sendto.assert_called_once()

    def test_process_besiege_settlement_event_client(self):
        """
        Ensure that game clients correctly process forwarded besiege settlement event packets.
        """
        besieging_player: Player = self.TEST_GAME_STATE.players[0]
        besieged_player: Player = self.TEST_GAME_STATE.players[1]
        unit: Unit = besieging_player.units[0]
        setl: Settlement = besieged_player.settlements[0]
        test_event: BesiegeSettlementEvent = BesiegeSettlementEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                                    UpdateAction.BESIEGE_SETTLEMENT,
                                                                    self.TEST_GAME_NAME, besieging_player.faction,
                                                                    unit.location, setl.name)
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # Neither the unit nor the settlement should be in a siege situation.
        self.assertFalse(unit.besieging)
        self.assertFalse(setl.besieged)

        # Process our test event.
        self.request_handler.process_besiege_settlement_event(test_event, self.mock_socket)

        # The unit should now be laying siege to the settlement, with this information not forwarded to the other
        # player, since this is a client.
        self.assertTrue(unit.besieging)
        self.assertTrue(setl.besieged)
        self.mock_socket.sendto.assert_not_called()

    def test_process_buyout_construction_event_server(self):
        """
        Ensure that the game server correctly processes buyout construction events.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        setl: Settlement = player.settlements[0]
        setl.current_work = Construction(IMPROVEMENTS[0], zeal_consumed=1.0)
        player.wealth = 2
        test_event: BuyoutConstructionEvent = BuyoutConstructionEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                                      UpdateAction.BUYOUT_CONSTRUCTION,
                                                                      self.TEST_GAME_NAME, player.faction, setl.name,
                                                                      player_wealth=1)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE

        # The settlement should have no improvements prior to buying out the construction.
        self.assertFalse(setl.improvements)

        # Process our test event.
        self.request_handler.process_buyout_construction_event(test_event, self.mock_socket)

        # The settlement's current work should now be completed, with the associated improvement added.
        self.assertIsNone(setl.current_work)
        self.assertTrue(setl.improvements)
        # The player's wealth should also now match the event.
        self.assertEqual(test_event.player_wealth, player.wealth)
        # Lastly, this information should have been forwarded by the server just once to the other player.
        self.mock_socket.sendto.assert_called_once()

    def test_process_buyout_construction_event_client(self):
        """
        Ensure that game clients correctly process buyout construction events.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        setl: Settlement = player.settlements[0]
        setl.current_work = Construction(IMPROVEMENTS[0], zeal_consumed=1.0)
        player.wealth = 2
        test_event: BuyoutConstructionEvent = BuyoutConstructionEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                                      UpdateAction.BUYOUT_CONSTRUCTION,
                                                                      self.TEST_GAME_NAME, player.faction, setl.name,
                                                                      player_wealth=1)
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # The settlement should have no improvements prior to buying out the construction.
        self.assertFalse(setl.improvements)

        # Process our test event.
        self.request_handler.process_buyout_construction_event(test_event, self.mock_socket)

        # The settlement's current work should now be completed, with the associated improvement added.
        self.assertIsNone(setl.current_work)
        self.assertTrue(setl.improvements)
        # The player's wealth should also now match the event.
        self.assertEqual(test_event.player_wealth, player.wealth)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

    def test_process_disband_unit_event_server(self):
        """
        Ensure that the game server correctly processes disband unit events.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        unit: Unit = player.units[0]
        test_event: DisbandUnitEvent = DisbandUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                        UpdateAction.DISBAND_UNIT, self.TEST_GAME_NAME, player.faction,
                                                        unit.location)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE

        # The player should have no wealth to begin with.
        self.assertFalse(player.wealth)

        # Process our test event.
        self.request_handler.process_disband_unit_event(test_event, self.mock_socket)

        # The player should now have wealth matching the cost recouped by disbanding the unit, thus also removing the
        # unit.
        self.assertEqual(unit.plan.cost, player.wealth)
        self.assertFalse(player.units)
        # This information should also have been forwarded by the server just once to the other player.
        self.mock_socket.sendto.assert_called_once()

    def test_process_disband_unit_event_client(self):
        """
        Ensure that game clients correctly process disband unit events.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        unit: Unit = player.units[0]
        test_event: DisbandUnitEvent = DisbandUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                        UpdateAction.DISBAND_UNIT, self.TEST_GAME_NAME, player.faction,
                                                        unit.location)
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # The player should have no wealth to begin with.
        self.assertFalse(player.wealth)

        # Process our test event.
        self.request_handler.process_disband_unit_event(test_event, self.mock_socket)

        # The player should now have wealth matching the cost recouped by disbanding the unit, thus also removing the
        # unit.
        self.assertEqual(unit.plan.cost, player.wealth)
        self.assertFalse(player.units)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

    def test_process_attack_unit_event_server(self):
        """
        Ensure that the game server correctly processes attack unit events involving other units.
        """
        attacking_player: Player = self.TEST_GAME_STATE.players[0]
        defending_player: Player = self.TEST_GAME_STATE.players[1]
        defending_player.units.append(self.TEST_UNIT_2)
        attacker: Unit = attacking_player.units[0]
        defender: Unit = defending_player.units[0]
        # Set both units health to 1 so we can simulate both units being killed.
        attacker.health = 1
        defender.health = 1
        test_event: AttackUnitEvent = AttackUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.ATTACK_UNIT,
                                                      self.TEST_GAME_NAME, attacking_player.faction, attacker.location,
                                                      defender.location)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE

        # Process our test event.
        self.request_handler.process_attack_unit_event(test_event, self.mock_socket)

        # Since both units only had 1 health, we expect both to have been killed and removed from their respective
        # player's units list.
        self.assertFalse(attacking_player.units)
        self.assertFalse(defending_player.units)
        # This information should also have been forwarded by the server just once to the other player.
        self.mock_socket.sendto.assert_called_once()

    def test_process_attack_unit_event_client(self):
        """
        Ensure that game clients correctly process attack unit events involving other units.
        """
        # For this test, we actually need an initialised board.
        self.TEST_GAME_STATE.board = Board(self.TEST_GAME_CONFIG, Namer(), {})
        board: Board = self.TEST_GAME_STATE.board
        # Simulate that the client is the defending player.
        self.TEST_GAME_STATE.player_idx = 1
        board.overlay.toggle_unit = MagicMock()
        board.overlay.toggle_attack = MagicMock()
        # Just set the attack time bank to something that isn't zero so we can see it being reset.
        board.attack_time_bank = 1
        attacking_player: Player = self.TEST_GAME_STATE.players[0]
        defending_player: Player = self.TEST_GAME_STATE.players[1]
        defending_player.units.append(self.TEST_UNIT_2)
        attacker: Unit = attacking_player.units[0]
        defender: Unit = defending_player.units[0]
        # Simulate the defending unit being currently selected on the board so that we can verify that it is unselected
        # when killed.
        board.selected_unit = defender
        # Set both units health to 1 so we can simulate both units being killed.
        attacker.health = 1
        defender.health = 1
        test_event: AttackUnitEvent = AttackUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.ATTACK_UNIT,
                                                      self.TEST_GAME_NAME, attacking_player.faction, attacker.location,
                                                      defender.location)
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # Process our test event.
        self.request_handler.process_attack_unit_event(test_event, self.mock_socket)

        # Since both units only had 1 health, we expect both to have been killed and removed from their respective
        # player's units list.
        self.assertFalse(attacking_player.units)
        self.assertFalse(defending_player.units)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()
        # We also expect the board to have been appropriately updated, given the selected unit was killed.
        self.assertIsNone(board.selected_unit)
        board.overlay.toggle_unit.assert_called_with(None)
        board.overlay.toggle_attack.assert_called()
        self.assertFalse(board.attack_time_bank)

    def test_process_attack_unit_event_heathen_server(self):
        """
        Ensure that the game server correctly processes attack unit events involving heathens.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        attacker: Unit = player.units[0]
        defender: Heathen = self.TEST_GAME_STATE.heathens[0]
        # Set the health of both combatants to 1 so we can simulate both being killed.
        attacker.health = 1
        defender.health = 1
        test_event: AttackUnitEvent = AttackUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.ATTACK_UNIT,
                                                      self.TEST_GAME_NAME, player.faction, attacker.location,
                                                      defender.location)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE

        # Process our test event.
        self.request_handler.process_attack_unit_event(test_event, self.mock_socket)

        # Since both combatants only had 1 health, we expect both to have been killed, with the attacker removed from
        # its player's units and the heathen removed from the game state.
        self.assertFalse(player.units)
        self.assertFalse(self.TEST_GAME_STATE.heathens)
        # This information should also have been forwarded by the server just once to the other player.
        self.mock_socket.sendto.assert_called_once()

    def test_process_attack_unit_event_heathen_client(self):
        """
        Ensure that game clients correctly process attack unit events involving heathens.
        """
        # For this test, we actually need an initialised board.
        self.TEST_GAME_STATE.board = Board(self.TEST_GAME_CONFIG, Namer(), {})
        board: Board = self.TEST_GAME_STATE.board
        board.overlay.toggle_unit = MagicMock()
        player: Player = self.TEST_GAME_STATE.players[0]
        attacker: Unit = player.units[0]
        defender: Heathen = self.TEST_GAME_STATE.heathens[0]
        # Simulate the heathen being currently selected on the board so that we can verify that it is unselected
        # when killed.
        board.selected_unit = defender
        # Set the health of both combatants to 1 so we can simulate both being killed.
        attacker.health = 1
        defender.health = 1
        test_event: AttackUnitEvent = AttackUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.ATTACK_UNIT,
                                                      self.TEST_GAME_NAME, player.faction, attacker.location,
                                                      defender.location)
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # Process our test event.
        self.request_handler.process_attack_unit_event(test_event, self.mock_socket)

        # Since both combatants only had 1 health, we expect both to have been killed, with the attacker removed from
        # its player's units and the heathen removed from the game state.
        self.assertFalse(player.units)
        self.assertFalse(self.TEST_GAME_STATE.heathens)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()
        # We also expect the board to have been appropriately updated, given the selected heathen was killed.
        self.assertIsNone(board.selected_unit)
        board.overlay.toggle_unit.assert_called_with(None)

    def test_process_attack_settlement_event_server(self):
        """
        Ensure that the game server correctly processes attack settlement events.
        """
        attacking_player: Player = self.TEST_GAME_STATE.players[0]
        attacking_player.units.append(self.TEST_UNIT_2)
        attacker: Unit = attacking_player.units[0]
        sieger: Unit = attacking_player.units[1]
        defending_player: Player = self.TEST_GAME_STATE.players[1]
        setl: Settlement = defending_player.settlements[0]
        # Set the health of the attacking unit to 1 and the strength of the settlement to 2 so we can simulate both the
        # attacking unit being killed and the settlement being taken.
        attacker.health = 1
        setl.strength = 2
        # Simulate a situation where the attacking player's units were laying siege to the settlement prior to attacking
        # it, placing them adjacent to the settlement.
        setl.besieged = True
        attacker.location = setl.location[0] - 1, setl.location[1]
        sieger.location = setl.location[0] + 1, setl.location[1]
        attacker.besieging = True
        sieger.besieging = True
        test_event: AttackSettlementEvent = AttackSettlementEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                                  UpdateAction.ATTACK_SETTLEMENT, self.TEST_GAME_NAME,
                                                                  attacking_player.faction, attacker.location,
                                                                  setl.name)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE

        # The attacking player should have no seen quads initially.
        self.assertFalse(attacking_player.quads_seen)

        # Process our test event.
        self.request_handler.process_attack_settlement_event(test_event, self.mock_socket)

        # The attacking unit should have been killed.
        self.assertNotIn(attacker, attacking_player.units)
        # The settlement should no longer be besieged since it was taken.
        self.assertFalse(setl.besieged)
        # The remaining unit laying siege that did not attack should no longer be doing so, since the settlement was
        # taken.
        self.assertFalse(sieger.besieging)
        # The settlement should have changed hands.
        self.assertIn(setl, attacking_player.settlements)
        self.assertFalse(defending_player.settlements)
        # The attacking player should also now have some seen quads around the settlement.
        self.assertTrue(attacking_player.quads_seen)
        # This information should also have been forwarded by the server just once to the other player.
        self.mock_socket.sendto.assert_called_once()

    def test_process_attack_settlement_event_client(self):
        """
        Ensure that game clients correctly process attack settlement events.
        """
        # For this test, we actually need an initialised board.
        self.TEST_GAME_STATE.board = Board(self.TEST_GAME_CONFIG, Namer(), {})
        board: Board = self.TEST_GAME_STATE.board
        # Simulate that the client is the defending player.
        self.TEST_GAME_STATE.player_idx = 1
        board.overlay.toggle_settlement = MagicMock()
        board.overlay.toggle_setl_attack = MagicMock()
        # Just set the attack time bank to something that isn't zero so we can see it being reset.
        board.attack_time_bank = 1

        attacking_player: Player = self.TEST_GAME_STATE.players[0]
        attacking_player.units.append(self.TEST_UNIT_2)
        attacker: Unit = attacking_player.units[0]
        sieger: Unit = attacking_player.units[1]
        defending_player: Player = self.TEST_GAME_STATE.players[1]
        setl: Settlement = defending_player.settlements[0]
        # Simulate the defending settlement being currently selected on the board so that we can verify that it is
        # unselected when taken.
        board.selected_settlement = setl

        # Set the health of the attacking unit to 1 and the strength of the settlement to 2 so we can simulate both the
        # attacking unit being killed and the settlement being taken.
        attacker.health = 1
        setl.strength = 2
        # Simulate a situation where the attacking player's units were laying siege to the settlement prior to attacking
        # it, placing them adjacent to the settlement.
        setl.besieged = True
        attacker.location = setl.location[0] - 1, setl.location[1]
        sieger.location = setl.location[0] + 1, setl.location[1]
        attacker.besieging = True
        sieger.besieging = True

        test_event: AttackSettlementEvent = AttackSettlementEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                                  UpdateAction.ATTACK_SETTLEMENT, self.TEST_GAME_NAME,
                                                                  attacking_player.faction, attacker.location,
                                                                  setl.name)
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # The attacking player should have no seen quads initially.
        self.assertFalse(attacking_player.quads_seen)

        # Process our test event.
        self.request_handler.process_attack_settlement_event(test_event, self.mock_socket)

        # The attacking unit should have been killed.
        self.assertNotIn(attacker, attacking_player.units)
        # The settlement should no longer be besieged since it was taken.
        self.assertFalse(setl.besieged)
        # The remaining unit laying siege that did not attack should no longer be doing so, since the settlement was
        # taken.
        self.assertFalse(sieger.besieging)
        # The settlement should have changed hands.
        self.assertIn(setl, attacking_player.settlements)
        self.assertFalse(defending_player.settlements)
        # The attacking player should also now have some seen quads around the settlement.
        self.assertTrue(attacking_player.quads_seen)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()
        # We also expect the board to have been appropriately updated, given the selected settlement was taken.
        self.assertIsNone(board.selected_settlement)
        board.overlay.toggle_settlement.assert_called_with(None, defending_player)
        board.overlay.toggle_setl_attack.assert_called()
        self.assertFalse(board.attack_time_bank)

    def test_process_heal_unit_event_server(self):
        """
        Ensure that the game server correctly processes heal unit events.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        player.units.append(self.TEST_HEALER_UNIT)
        healer: Unit = player.units[1]
        healed: Unit = player.units[0]
        # Obviously there's no way a unit could have zero health and still be alive, but it makes testing easier.
        healed.health = 0
        test_event: HealUnitEvent = HealUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.HEAL_UNIT,
                                                  self.TEST_GAME_NAME, player.faction, healer.location, healed.location)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE

        # The healer should not have acted prior to the event being processed.
        self.assertFalse(healer.has_acted)

        # Process our test event.
        self.request_handler.process_heal_unit_event(test_event, self.mock_socket)

        # The unit being healed should now have health equal to the healer unit's power, and naturally the healer should
        # have acted.
        self.assertEqual(healer.plan.power, healed.health)
        self.assertTrue(healer.has_acted)
        # This information should also have been forwarded by the server just once to the other player.
        self.mock_socket.sendto.assert_called_once()

    def test_process_heal_unit_event_client(self):
        """
        Ensure that game clients correctly process heal unit events.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        player.units.append(self.TEST_HEALER_UNIT)
        healer: Unit = player.units[1]
        healed: Unit = player.units[0]
        # Obviously there's no way a unit could have zero health and still be alive, but it makes testing easier.
        healed.health = 0
        test_event: HealUnitEvent = HealUnitEvent(EventType.UPDATE, self.TEST_IDENTIFIER, UpdateAction.HEAL_UNIT,
                                                  self.TEST_GAME_NAME, player.faction, healer.location, healed.location)
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # The healer should not have acted prior to the event being processed.
        self.assertFalse(healer.has_acted)

        # Process our test event.
        self.request_handler.process_heal_unit_event(test_event, self.mock_socket)

        # The unit being healed should now have health equal to the healer unit's power, and naturally the healer should
        # have acted.
        self.assertEqual(healer.plan.power, healed.health)
        self.assertTrue(healer.has_acted)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

    def test_process_board_deployer_event_server(self):
        """
        Ensure that the game server correctly processes board deployer events.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        unit: Unit = player.units[0]
        unit.remaining_stamina = 1
        player.units.append(self.TEST_DEPLOYER_UNIT)
        deployer: DeployerUnit = player.units[1]
        test_event: BoardDeployerEvent = BoardDeployerEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                            UpdateAction.BOARD_DEPLOYER, self.TEST_GAME_NAME,
                                                            player.faction, unit.location, deployer.location,
                                                            new_stamina=0)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE

        # The deployer unit should have no passengers to begin with, and the player should have both it and another unit
        # deployed on the board.
        self.assertFalse(deployer.passengers)
        self.assertEqual(2, len(player.units))

        # Process our test event.
        self.request_handler.process_board_deployer_event(test_event, self.mock_socket)

        # The unit's stamina should have been updated according to the event.
        self.assertEqual(test_event.new_stamina, unit.remaining_stamina)
        # The unit should also now be a passenger of the deployer unit, and no longer part of the player's overall
        # units.
        self.assertListEqual([unit], deployer.passengers)
        self.assertListEqual([deployer], player.units)
        # Lastly, this information should have been forwarded by the server just once to the other player.
        self.mock_socket.sendto.assert_called_once()

    def test_process_board_deployer_event_client(self):
        """
        Ensure that game clients correctly process board deployer events.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        unit: Unit = player.units[0]
        unit.remaining_stamina = 1
        player.units.append(self.TEST_DEPLOYER_UNIT)
        deployer: DeployerUnit = player.units[1]
        test_event: BoardDeployerEvent = BoardDeployerEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                            UpdateAction.BOARD_DEPLOYER, self.TEST_GAME_NAME,
                                                            player.faction, unit.location, deployer.location,
                                                            new_stamina=0)
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # The deployer unit should have no passengers to begin with, and the player should have both it and another unit
        # deployed on the board.
        self.assertFalse(deployer.passengers)
        self.assertEqual(2, len(player.units))

        # Process our test event.
        self.request_handler.process_board_deployer_event(test_event, self.mock_socket)

        # The unit's stamina should have been updated according to the event.
        self.assertEqual(test_event.new_stamina, unit.remaining_stamina)
        # The unit should also now be a passenger of the deployer unit, and no longer part of the player's overall
        # units.
        self.assertListEqual([unit], deployer.passengers)
        self.assertListEqual([deployer], player.units)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

    def test_process_deployer_deploy_event_server(self):
        """
        Ensure that the game server correctly processes deployer deploy events.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        player.units = [self.TEST_DEPLOYER_UNIT]
        deployer: DeployerUnit = player.units[0]
        deployer.passengers = [self.TEST_UNIT]
        deployed: Unit = deployer.passengers[0]
        test_event: DeployerDeployEvent = DeployerDeployEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                              UpdateAction.DEPLOYER_DEPLOY, self.TEST_GAME_NAME,
                                                              player.faction, deployer.location, passenger_idx=0,
                                                              deployed_loc=(10, 10))
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE

        # The player should not have seen any quads initially.
        self.assertFalse(player.quads_seen)

        # Process our test event.
        self.request_handler.process_deployer_deploy_event(test_event, self.mock_socket)

        # The unit should have been deployed at the appropriate location.
        self.assertTupleEqual(test_event.deployed_loc, deployed.location)
        # The deployer unit should now have no passengers.
        self.assertFalse(deployer.passengers)
        # The player should now have two deployed units, and have seen some quads.
        self.assertListEqual([deployer, deployed], player.units)
        self.assertTrue(player.quads_seen)
        # Lastly, this information should have been forwarded by the server just once to the other player.
        self.mock_socket.sendto.assert_called_once()

    def test_process_deployer_deploy_event_client(self):
        """
        Ensure that game clients correctly process deployer deploy events.
        """
        player: Player = self.TEST_GAME_STATE.players[0]
        player.units = [self.TEST_DEPLOYER_UNIT]
        deployer: DeployerUnit = player.units[0]
        deployer.passengers = [self.TEST_UNIT]
        deployed: Unit = deployer.passengers[0]
        test_event: DeployerDeployEvent = DeployerDeployEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                              UpdateAction.DEPLOYER_DEPLOY, self.TEST_GAME_NAME,
                                                              player.faction, deployer.location, passenger_idx=0,
                                                              deployed_loc=(10, 10))
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # The player should not have seen any quads initially.
        self.assertFalse(player.quads_seen)

        # Process our test event.
        self.request_handler.process_deployer_deploy_event(test_event, self.mock_socket)

        # The unit should have been deployed at the appropriate location.
        self.assertTupleEqual(test_event.deployed_loc, deployed.location)
        # The deployer unit should now have no passengers.
        self.assertFalse(deployer.passengers)
        # The player should now have two deployed units, and have seen some quads.
        self.assertListEqual([deployer, deployed], player.units)
        self.assertTrue(player.quads_seen)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

    def test_process_query_event_server(self):
        """
        Ensure that the game server correctly processes query events.
        """
        # Add an AI player to the game so we can see how their details are included as well.
        ai_player: Player = Player("Mr. Roboto", Faction.FUNDAMENTALISTS, 2,
                                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL))
        self.TEST_GAME_STATE.players.append(ai_player)
        # Simulate that the game has started so we can validate the turn being used.
        self.TEST_GAME_STATE.game_started = True
        self.TEST_GAME_STATE.turn = 10
        # Use a different GameConfig that allows for three players.
        three_player_conf: GameConfig = \
            GameConfig(3, Faction.AGRICULTURISTS, True, True, True, MultiplayerStatus.GLOBAL)
        test_event: QueryEvent = QueryEvent(EventType.QUERY, self.TEST_IDENTIFIER)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE
        self.mock_server.lobbies_ref[self.TEST_GAME_NAME] = three_player_conf

        # Process our test event.
        self.request_handler.process_query_event(test_event, self.mock_socket)

        # Extract out our expected data into a couple of variables since this logic is a little more complicated.
        expected_player_details: List[PlayerDetails] = []
        # The player details for the human players should have been retrieved directly from the game clients for this
        # game.
        expected_player_details.extend(self.mock_server.game_clients_ref[self.TEST_GAME_NAME])
        # However, the AI player should have had their details manually added.
        expected_player_details.append(PlayerDetails(ai_player.name, ai_player.faction, id=None))
        # The lobby returned should have the correct name, config, turn, and player details.
        expected_lobby: LobbyDetails = LobbyDetails(self.TEST_GAME_NAME, expected_player_details,
                                                    three_player_conf, self.TEST_GAME_STATE.turn)

        # Ensure the lobby is returned as expected.
        self.assertListEqual([expected_lobby], test_event.lobbies)
        # We also expect the server to have sent a packet containing a JSON representation of the event to the client
        # that originally dispatched the query event.
        self.mock_socket.sendto.assert_called_with(json.dumps(test_event, cls=SaveEncoder).encode(),
                                                   (self.TEST_HOST, self.TEST_PORT))

    def test_process_query_event_client(self):
        """
        Ensure that game clients correctly process query events.
        """
        test_lobby: LobbyDetails = LobbyDetails(self.TEST_GAME_NAME,
                                                self.mock_server.game_clients_ref[self.TEST_GAME_NAME],
                                                self.TEST_GAME_CONFIG,
                                                self.TEST_GAME_STATE.turn)
        test_event: QueryEvent = QueryEvent(EventType.QUERY, self.TEST_IDENTIFIER, lobbies=[test_lobby])
        self.mock_server.is_server = False
        menu: Menu = self.mock_server.game_controller_ref.menu

        # The client should have no lobbies present initially, and thus should not be viewing them.
        self.assertFalse(menu.multiplayer_lobbies)
        self.assertFalse(menu.viewing_lobbies)

        # Process our test event, simulating a response from the global game server.
        self.request_handler.client_address = (GLOBAL_SERVER_HOST,)
        self.request_handler.process_query_event(test_event, self.mock_socket)

        # The lobbies from the event should now be both present and being viewed in the client's menu.
        self.assertListEqual(test_event.lobbies, menu.multiplayer_lobbies)
        self.assertTrue(menu.viewing_lobbies)
        # However, because the response was from the global game server, we expect to not be viewing local lobbies.
        self.assertFalse(menu.viewing_local_lobbies)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

        # Now process our test event again, but this time simulate a response from a local game server.
        self.request_handler.client_address = ("127.0.0.1",)
        self.request_handler.process_query_event(test_event, self.mock_socket)

        # The lobbies from the event should still be both present and being viewed in the client's menu.
        self.assertListEqual(test_event.lobbies, menu.multiplayer_lobbies)
        self.assertTrue(menu.viewing_lobbies)
        # However, this time we expect to also be viewing local lobbies.
        self.assertTrue(menu.viewing_local_lobbies)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

    def test_process_leave_event_server(self):
        """
        Ensure that the game server correctly processes leave events.
        """
        # We need to disable the pylint rule against protected access since we're going to be testing an internal method
        # in this test.
        # pylint: disable=protected-access
        # Simulate a situation in which a two-player game is in progress, with one player having already ended their
        # turn.
        self.TEST_GAME_STATE.game_started = True
        self.TEST_GAME_STATE.ready_players = {self.TEST_IDENTIFIER_2}
        test_event: LeaveEvent = LeaveEvent(EventType.LEAVE, self.TEST_IDENTIFIER, self.TEST_GAME_NAME)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE
        leaving_player: Player = self.TEST_GAME_STATE.players[0]
        other_player_details: PlayerDetails = self.mock_server.game_clients_ref[self.TEST_GAME_NAME][1]
        # Mock out the end turn function since there's really no need to test it here.
        self.request_handler._server_end_turn = MagicMock()

        # The player that is leaving should obviously have no AI playstyle initially.
        self.assertIsNone(leaving_player.ai_playstyle)
        # Process our test event.
        self.request_handler.process_leave_event(test_event, self.mock_socket)
        # There should now only be the other player as a game client.
        self.assertDictEqual({self.TEST_GAME_NAME: [other_player_details]}, self.mock_server.game_clients_ref)
        # The player that left should now have an AI playstyle, which, along with their faction, should have been
        # forwarded on just once to the remaining player.
        self.assertIsNotNone(leaving_player.ai_playstyle)
        self.assertEqual(leaving_player.ai_playstyle, test_event.player_ai_playstyle)
        self.assertEqual(leaving_player.faction, test_event.leaving_player_faction)
        self.mock_socket.sendto.assert_called_once()
        # We also expect the turn to have been ended, since the remaining player had already ended their turn.
        self.request_handler._server_end_turn.assert_called_with(self.TEST_GAME_STATE,
                                                                 EndTurnEvent(EventType.END_TURN, None,
                                                                              self.TEST_GAME_NAME),
                                                                 self.mock_socket)

        # Now we simulate the remaining player leaving as well.
        test_event.identifier = self.TEST_IDENTIFIER_2
        self.request_handler.process_leave_event(test_event, self.mock_socket)
        # The game server should have purged all references to the game since there are no longer any players.
        self.assertNotIn(self.TEST_GAME_NAME, self.mock_server.game_clients_ref)
        self.assertNotIn(self.TEST_GAME_NAME, self.mock_server.lobbies_ref)
        self.assertNotIn(self.TEST_GAME_NAME, self.mock_server.game_states_ref)
        # No further packets should have been forwarded, nor turns ended.
        self.mock_socket.sendto.assert_called_once()
        self.request_handler._server_end_turn.assert_called_once()

    def test_process_leave_event_client(self):
        """
        Ensure that game clients correctly respond to leave events.
        """
        # For this test, we actually need an initialised board.
        self.TEST_GAME_STATE.board = Board(self.TEST_GAME_CONFIG, Namer(), {})
        self.TEST_GAME_STATE.board.overlay.toggle_player_change = MagicMock()
        player: Player = self.TEST_GAME_STATE.players[0]
        player_details: PlayerDetails = self.mock_server.game_clients_ref[self.TEST_GAME_NAME][0]
        test_event: LeaveEvent = LeaveEvent(EventType.LEAVE, self.TEST_IDENTIFIER, self.TEST_GAME_NAME,
                                            player.faction, AIPlaystyle(AttackPlaystyle.NEUTRAL,
                                                                        ExpansionPlaystyle.NEUTRAL))
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE
        self.mock_server.game_controller_ref.menu.multiplayer_lobby = \
            LobbyDetails("Cool", self.mock_server.game_clients_ref[self.TEST_GAME_NAME], self.TEST_GAME_CONFIG, None)

        # First simulate the situation in which another player has left an ongoing game.
        self.TEST_GAME_STATE.game_started = True
        self.assertIsNone(player.ai_playstyle)
        self.request_handler.process_leave_event(test_event, self.mock_socket)
        # We expect the leaving player to now have an AI playstyle in accordance with the event, and for the local
        # player's overlay to denote that the player has left.
        self.assertEqual(test_event.player_ai_playstyle, player.ai_playstyle)
        self.TEST_GAME_STATE.board.overlay.toggle_player_change.assert_called_with(player,
                                                                                   changed_player_is_leaving=True)

        # Now simulate the situation where a player is leaving a game that has not yet started.
        self.TEST_GAME_STATE.game_started = False
        self.request_handler.process_leave_event(test_event, self.mock_socket)
        # The leaving player should have been removed from both the game state and the lobby itself.
        self.assertNotIn(player, self.TEST_GAME_STATE.players)
        self.assertNotIn(player_details, self.mock_server.game_controller_ref.menu.multiplayer_lobby.current_players)

    @patch("time.sleep", lambda *args: None)
    @patch("random.choice")
    def test_process_join_event_server_in_lobby(self, random_choice_mock: MagicMock):
        """
        Ensure that the game server correctly processes join events when the game being joined has not yet started.
        """
        gs: GameState = self.TEST_GAME_STATE
        # To verify that AI and human player details are returned differently, we need an AI player in the lobby as
        # well.
        ai_player: Player = Player("Mr. Roboto", Faction.FUNDAMENTALISTS, FACTION_COLOURS[Faction.FUNDAMENTALISTS],
                                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL))
        gs.players.append(ai_player)
        gs.game_started = False
        # Make the first player an AI too so that we can see them getting kicked out to make way for the joining client.
        player_to_be_removed: Player = gs.players[0]
        player_to_be_removed.ai_playstyle = AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)
        # Simulate the randomly-generated player name conflicting with an existing name in the lobby, and then selecting
        # a non-conflicting one.
        random_choice_mock.side_effect = [gs.players[1].name, PLAYER_NAMES[0]]

        test_event: JoinEvent = JoinEvent(EventType.JOIN, self.TEST_IDENTIFIER, self.TEST_GAME_NAME, Faction.GODLESS)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = gs
        # Out of the three players in the lobby, one is currently a human player.
        other_client_details: PlayerDetails = PlayerDetails("Dos", Faction.FRONTIERSMEN, self.TEST_IDENTIFIER_2)
        # Since the first and third players are AIs, they shouldn't be in the game clients.
        self.mock_server.game_clients_ref = {
            self.TEST_GAME_NAME: [other_client_details]
        }
        # Use a different GameConfig that allows for three players.
        three_player_conf: GameConfig = \
            GameConfig(3, Faction.AGRICULTURISTS, True, True, True, MultiplayerStatus.GLOBAL)
        self.mock_server.lobbies_ref[self.TEST_GAME_NAME] = three_player_conf

        # Process our test event.
        self.request_handler.process_join_event(test_event, self.mock_socket)

        # Declare some of the more complicated expected state separately for clarity.
        # We expect the player joining the lobby to have the appropriate name, as well as the faction and identifier
        # from the event.
        expected_new_player_details: PlayerDetails = \
            PlayerDetails(PLAYER_NAMES[0], test_event.player_faction, test_event.identifier)
        # The AI player's details shouldn't have an identifier.
        expected_ai_player_details: PlayerDetails = PlayerDetails(ai_player.name, ai_player.faction, id=None)
        # The lobby should have the name from the event, the expected details from each player, the correct
        # configuration, but no turn since the game has not yet started.
        expected_lobby_details: LobbyDetails = \
            LobbyDetails(test_event.lobby_name,
                         # Note the order here - since the joining player is a new player altogether, the other two
                         # players have each shifted back one in their player index.
                         [other_client_details, expected_ai_player_details, expected_new_player_details],
                         three_player_conf,
                         current_turn=None)

        # The first AI player should have been removed to make way for the joining client.
        self.assertNotIn(player_to_be_removed, gs.players)
        # There should still be three players however, as the new client should be tacked on the end.
        self.assertEqual(3, len(gs.players))
        # The new player should have the expected name and faction.
        self.assertEqual(Player(PLAYER_NAMES[0], test_event.player_faction, FACTION_COLOURS[test_event.player_faction]),
                         gs.players[2])
        # The game clients for this lobby should now consist of both the original client and the new joining one.
        self.assertListEqual([other_client_details, expected_new_player_details],
                             self.mock_server.game_clients_ref[test_event.lobby_name])
        self.assertEqual(expected_lobby_details, test_event.lobby_details)

        # We expect both clients to have been notified that the player joined the lobby successfully.
        self.assertEqual(2, len(self.mock_socket.sendto.mock_calls))

    @patch("time.sleep", lambda *args: None)
    def test_process_join_event_server_game_started(self):
        """
        Ensure that the game server correctly processes join events when the game being joined is already underway.
        """
        gs: GameState = self.TEST_GAME_STATE
        # To verify that AI and human player details are returned differently, we need an AI player in the game as well.
        ai_player: Player = Player("Mr. Roboto", Faction.FUNDAMENTALISTS, FACTION_COLOURS[Faction.FUNDAMENTALISTS],
                                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL))
        gs.players.append(ai_player)
        # Give each player some seen quads so we can see the minified packet representations them being sent back to the
        # joining client. We use a list here so that the order is consistent.
        test_seen_quads: List[Tuple[int, int]] = [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]
        for p in gs.players:
            p.quads_seen = test_seen_quads
        gs.game_started = True
        # The below values obviously can't occur simultaneously, but we want to show that the server responds correctly
        # and assigns these values to the forwarded event.
        gs.until_night = 1
        gs.nighttime_left = 1
        # Make the first player an AI as well so that a client can join as them in this test.
        replaced_player: Player = gs.players[0]
        replaced_player.ai_playstyle = AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)
        # For this test, we actually need an initialised board.
        gs.board = Board(self.TEST_GAME_CONFIG, Namer(), {})

        test_event: JoinEvent = JoinEvent(EventType.JOIN, self.TEST_IDENTIFIER, self.TEST_GAME_NAME,
                                          replaced_player.faction)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = gs
        # Out of the three players in the game, one is currently a human player.
        other_client_details: PlayerDetails = PlayerDetails("Dos", Faction.FRONTIERSMEN, self.TEST_IDENTIFIER_2)
        # Since the first and third players are AIs, they shouldn't be in the game clients.
        self.mock_server.game_clients_ref = {
            self.TEST_GAME_NAME: [other_client_details]
        }
        # Use a different GameConfig that allows for three players.
        three_player_conf: GameConfig = \
            GameConfig(3, Faction.AGRICULTURISTS, True, True, True, MultiplayerStatus.GLOBAL)
        self.mock_server.lobbies_ref[self.TEST_GAME_NAME] = three_player_conf

        # Process our test event.
        self.request_handler.process_join_event(test_event, self.mock_socket)

        # Declare some of the more complicated expected state separately for clarity.
        # We expect the player being replaced to now be represented as a human client, using the joining player's
        # identifier.
        expected_replaced_player_details: PlayerDetails = \
            PlayerDetails(replaced_player.name, replaced_player.faction, test_event.identifier)
        # The AI player's details shouldn't have an identifier.
        expected_ai_player_details: PlayerDetails = PlayerDetails(ai_player.name, ai_player.faction, id=None)
        # The lobby should have the name from the event, the expected details from each player, and the correct
        # configuration and turn.
        expected_lobby_details: LobbyDetails = \
            LobbyDetails(test_event.lobby_name,
                         [expected_replaced_player_details, other_client_details, expected_ai_player_details],
                         three_player_conf,
                         gs.turn)

        # Naturally, the replaced player should no longer have an AI playstyle.
        self.assertIsNone(replaced_player.ai_playstyle)
        # The game clients for this game should now consist of both the original client and the new joining one.
        self.assertListEqual([other_client_details, expected_replaced_player_details],
                             self.mock_server.game_clients_ref[test_event.lobby_name])
        self.assertEqual(expected_lobby_details, test_event.lobby_details)

        # Because there are a number of different types of JoinEvents fired off by the server to clients, we need to
        # distinguish the five types using separate methods.

        def is_standard_packet(c: call) -> bool:
            """
            Get whether the supplied mock call to the mock socket was representative of a standard JoinEvent with no
            extra fields. This standard type is sent to all clients already in the game the new client is joining.
            :param c: The mock call being checked.
            :return: Whether the mock call originates from a standard JoinEvent.
            """
            evt: JoinEvent = json.loads(c.args[0], object_hook=ObjectConverter)
            return evt.quad_chunk is None and \
                evt.player_chunk is None and \
                evt.quads_seen_chunk is None and \
                evt.heathens_chunk is None

        def is_quad_and_cfg_packet(c: call) -> bool:
            """
            Get whether the supplied mock call to the mock socket was representative of a JoinEvent containing quad and
            overall game configuration data. This type is sent only to the client joining the game.
            :param c: The mock call being checked.
            :return: Whether the mock call originates from a quad and config JoinEvent.
            """
            evt: JoinEvent = json.loads(c.args[0], object_hook=ObjectConverter)
            return evt.quad_chunk is not None

        def is_player_packet(c: call) -> bool:
            """
            Get whether the supplied mock call to the mock socket was representative of a JoinEvent containing player
            data. This type is sent only to the client joining the game.
            :param c: The mock call being checked.
            :return: Whether the mock call originates from a player JoinEvent.
            """
            evt: JoinEvent = json.loads(c.args[0], object_hook=ObjectConverter)
            return evt.player_chunk is not None

        def is_quads_seen_packet(c: call) -> bool:
            """
            Get whether the supplied mock call to the mock socket was representative of a JoinEvent containing seen
            quads data for each player. This type is sent only to the client joining the game.
            :param c: The mock call being checked.
            :return: Whether the mock call originates from a seen quads JoinEvent.
            """
            evt: JoinEvent = json.loads(c.args[0], object_hook=ObjectConverter)
            return evt.quads_seen_chunk is not None

        def is_heathens_packet(c: call) -> bool:
            """
            Get whether the supplied mock call to the mock socket was representative of a JoinEvent containing heathen
            data. This type is sent only to the client joining the game.
            :param c: The mock call being checked.
            :return: Whether the mock call originates from a heathen JoinEvent.
            """
            evt: JoinEvent = json.loads(c.args[0], object_hook=ObjectConverter)
            return evt.heathens_chunk is not None

        # We expect the other client to have been notified that the player joined.
        standard_packets: List[call] = [c for c in self.mock_socket.sendto.mock_calls if is_standard_packet(c)]
        self.assertEqual(1, len(standard_packets))

        quad_and_cfg_packets: List[JoinEvent] = [json.loads(c.args[0], object_hook=ObjectConverter)
                                                 for c in self.mock_socket.sendto.mock_calls
                                                 if is_quad_and_cfg_packet(c)]
        # We expect there to have been 90 packets sent back to the joining client with quad data. This is because there
        # are 9000 quads on the board, and they are sent in chunks of 100.
        self.assertEqual(90, len(quad_and_cfg_packets))
        for pkt in quad_and_cfg_packets:
            # Validate that the game configuration was appropriately returned.
            self.assertEqual(gs.until_night, pkt.until_night)
            self.assertEqual(gs.nighttime_left, pkt.nighttime_left)
            # We need to compare the object's dictionary forms as one is a GameConfig and one is an ObjectConverter.
            self.assertEqual(three_player_conf.__dict__, pkt.cfg.__dict__)

        player_packets: List[JoinEvent] = [json.loads(c.args[0], object_hook=ObjectConverter)
                                           for c in self.mock_socket.sendto.mock_calls if is_player_packet(c)]
        # The joining client should have been sent three packets of player data, each containing the data for a single
        # player in the game.
        self.assertEqual(3, len(player_packets))
        for i in range(len(player_packets)):
            self.assertEqual(minify_player(gs.players[i]), player_packets[i].player_chunk)
            self.assertEqual(i, player_packets[i].player_chunk_idx)

        quads_seen_packets: List[JoinEvent] = [json.loads(c.args[0], object_hook=ObjectConverter)
                                               for c in self.mock_socket.sendto.mock_calls if is_quads_seen_packet(c)]
        # The joining client should have been sent three packets of seen quad data, each containing the data for a
        # single player's seen quads.
        self.assertEqual(3, len(quads_seen_packets))
        for i in range(len(quads_seen_packets)):
            self.assertEqual(minify_quads_seen(set(gs.players[i].quads_seen)), quads_seen_packets[i].quads_seen_chunk)
            self.assertEqual(i, quads_seen_packets[i].player_chunk_idx)

        heathens_packets: List[JoinEvent] = [json.loads(c.args[0], object_hook=ObjectConverter)
                                             for c in self.mock_socket.sendto.mock_calls if is_heathens_packet(c)]
        # Lastly, we expect the joining client to have been sent a single packet containing data about the heathens
        # currently in the game.
        self.assertEqual(1, len(heathens_packets))
        self.assertEqual(minify_heathens(gs.heathens), heathens_packets[0].heathens_chunk)
        self.assertEqual(len(gs.heathens), heathens_packets[0].total_heathens)

    @patch("time.sleep", lambda *args: None)
    def test_process_join_event_server_game_started_client_is_rejoining(self):
        """
        Ensure that the game server correctly processes join events when the game being joined is already underway, and
        the client is rejoining the game.
        """
        gs: GameState = self.TEST_GAME_STATE
        # To verify that AI and human player details are returned differently, we need an AI player in the game as well.
        ai_player: Player = Player("Mr. Roboto", Faction.FUNDAMENTALISTS, FACTION_COLOURS[Faction.FUNDAMENTALISTS],
                                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL))
        gs.players.append(ai_player)
        # Give each player some seen quads so we can see the minified packet representations them being sent back to the
        # rejoining client. We use a list here so that the order is consistent.
        test_seen_quads: List[Tuple[int, int]] = [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]
        for p in gs.players:
            p.quads_seen = test_seen_quads
        gs.game_started = True
        # The below values obviously can't occur simultaneously, but we want to show that the server responds correctly
        # and assigns these values to the forwarded event.
        gs.until_night = 1
        gs.nighttime_left = 1
        # Simulate a situation in which the first player is rejoining the game after losing sync with the server.
        rejoining_player: Player = gs.players[0]
        # For this test, we actually need an initialised board.
        gs.board = Board(self.TEST_GAME_CONFIG, Namer(), {})

        test_event: JoinEvent = JoinEvent(EventType.JOIN, self.TEST_IDENTIFIER, self.TEST_GAME_NAME,
                                          rejoining_player.faction)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = gs
        # Out of the three players in the game, two are currently human players.
        rejoining_client_details: PlayerDetails = PlayerDetails("Uno", Faction.AGRICULTURISTS, self.TEST_IDENTIFIER)
        other_client_details: PlayerDetails = PlayerDetails("Dos", Faction.FRONTIERSMEN, self.TEST_IDENTIFIER_2)
        # Since the third player is an AI, they shouldn't be in the game clients.
        self.mock_server.game_clients_ref = {
            self.TEST_GAME_NAME: [rejoining_client_details, other_client_details]
        }
        # Use a different GameConfig that allows for three players.
        three_player_conf: GameConfig = \
            GameConfig(3, Faction.AGRICULTURISTS, True, True, True, MultiplayerStatus.GLOBAL)
        self.mock_server.lobbies_ref[self.TEST_GAME_NAME] = three_player_conf

        # Process our test event.
        self.request_handler.process_join_event(test_event, self.mock_socket)

        # Declare some of the more complicated expected state separately for clarity.
        # The AI player's details shouldn't have an identifier.
        expected_ai_player_details: PlayerDetails = PlayerDetails(ai_player.name, ai_player.faction, id=None)
        # The lobby should have the name from the event, the expected details from each player, and the correct
        # configuration and turn.
        expected_lobby_details: LobbyDetails = \
            LobbyDetails(test_event.lobby_name,
                         [rejoining_client_details, other_client_details, expected_ai_player_details],
                         three_player_conf,
                         gs.turn)

        # The game clients for this game should be unchanged, as the client was rejoining.
        self.assertListEqual([rejoining_client_details, other_client_details],
                             self.mock_server.game_clients_ref[test_event.lobby_name])
        self.assertEqual(expected_lobby_details, test_event.lobby_details)

        # Because there are a number of different types of JoinEvents fired off by the server to clients, we need to
        # distinguish the five types using separate methods.

        def is_standard_packet(c: call) -> bool:
            """
            Get whether the supplied mock call to the mock socket was representative of a standard JoinEvent with no
            extra fields. This standard type is sent to all clients already in the game the new client is joining.
            :param c: The mock call being checked.
            :return: Whether the mock call originates from a standard JoinEvent.
            """
            evt: JoinEvent = json.loads(c.args[0], object_hook=ObjectConverter)
            return evt.quad_chunk is None and \
                evt.player_chunk is None and \
                evt.quads_seen_chunk is None and \
                evt.heathens_chunk is None

        def is_quad_and_cfg_packet(c: call) -> bool:
            """
            Get whether the supplied mock call to the mock socket was representative of a JoinEvent containing quad and
            overall game configuration data. This type is sent only to the client joining the game.
            :param c: The mock call being checked.
            :return: Whether the mock call originates from a quad and config JoinEvent.
            """
            evt: JoinEvent = json.loads(c.args[0], object_hook=ObjectConverter)
            return evt.quad_chunk is not None

        def is_player_packet(c: call) -> bool:
            """
            Get whether the supplied mock call to the mock socket was representative of a JoinEvent containing player
            data. This type is sent only to the client joining the game.
            :param c: The mock call being checked.
            :return: Whether the mock call originates from a player JoinEvent.
            """
            evt: JoinEvent = json.loads(c.args[0], object_hook=ObjectConverter)
            return evt.player_chunk is not None

        def is_quads_seen_packet(c: call) -> bool:
            """
            Get whether the supplied mock call to the mock socket was representative of a JoinEvent containing seen
            quads data for each player. This type is sent only to the client joining the game.
            :param c: The mock call being checked.
            :return: Whether the mock call originates from a seen quads JoinEvent.
            """
            evt: JoinEvent = json.loads(c.args[0], object_hook=ObjectConverter)
            return evt.quads_seen_chunk is not None

        def is_heathens_packet(c: call) -> bool:
            """
            Get whether the supplied mock call to the mock socket was representative of a JoinEvent containing heathen
            data. This type is sent only to the client joining the game.
            :param c: The mock call being checked.
            :return: Whether the mock call originates from a heathen JoinEvent.
            """
            evt: JoinEvent = json.loads(c.args[0], object_hook=ObjectConverter)
            return evt.heathens_chunk is not None

        # We expect the other client not to have been notified, since the client was only rejoining.
        standard_packets: List[call] = [c for c in self.mock_socket.sendto.mock_calls if is_standard_packet(c)]
        self.assertFalse(standard_packets)

        quad_and_cfg_packets: List[JoinEvent] = [json.loads(c.args[0], object_hook=ObjectConverter)
                                                 for c in self.mock_socket.sendto.mock_calls
                                                 if is_quad_and_cfg_packet(c)]
        # We expect there to have been 90 packets sent back to the rejoining client with quad data. This is because
        # there are 9000 quads on the board, and they are sent in chunks of 100.
        self.assertEqual(90, len(quad_and_cfg_packets))
        for pkt in quad_and_cfg_packets:
            # Validate that the game configuration was appropriately returned.
            self.assertEqual(gs.until_night, pkt.until_night)
            self.assertEqual(gs.nighttime_left, pkt.nighttime_left)
            # We need to compare the object's dictionary forms as one is a GameConfig and one is an ObjectConverter.
            self.assertEqual(three_player_conf.__dict__, pkt.cfg.__dict__)

        player_packets: List[JoinEvent] = [json.loads(c.args[0], object_hook=ObjectConverter)
                                           for c in self.mock_socket.sendto.mock_calls if is_player_packet(c)]
        # The rejoining client should have been sent three packets of player data, each containing the data for a single
        # player in the game.
        self.assertEqual(3, len(player_packets))
        for i in range(len(player_packets)):
            self.assertEqual(minify_player(gs.players[i]), player_packets[i].player_chunk)
            self.assertEqual(i, player_packets[i].player_chunk_idx)

        quads_seen_packets: List[JoinEvent] = [json.loads(c.args[0], object_hook=ObjectConverter)
                                               for c in self.mock_socket.sendto.mock_calls if is_quads_seen_packet(c)]
        # The rejoining client should have been sent three packets of seen quad data, each containing the data for a
        # single player's seen quads.
        self.assertEqual(3, len(quads_seen_packets))
        for i in range(len(quads_seen_packets)):
            self.assertEqual(minify_quads_seen(set(gs.players[i].quads_seen)), quads_seen_packets[i].quads_seen_chunk)
            self.assertEqual(i, quads_seen_packets[i].player_chunk_idx)

        heathens_packets: List[JoinEvent] = [json.loads(c.args[0], object_hook=ObjectConverter)
                                             for c in self.mock_socket.sendto.mock_calls if is_heathens_packet(c)]
        # Lastly, we expect the rejoining client to have been sent a single packet containing data about the heathens
        # currently in the game.
        self.assertEqual(1, len(heathens_packets))
        self.assertEqual(minify_heathens(gs.heathens), heathens_packets[0].heathens_chunk)
        self.assertEqual(len(gs.heathens), heathens_packets[0].total_heathens)

    def test_process_join_event_client_joining_lobby(self):
        """
        Ensure that game clients process join events correctly when the client is joining an existing lobby.
        """
        test_lobby_details: LobbyDetails = LobbyDetails(self.TEST_GAME_NAME,
                                                        # Just use our test game clients - we're simulating a situation
                                                        # where the client has just joined as the second player.
                                                        self.mock_server.game_clients_ref[self.TEST_GAME_NAME],
                                                        self.TEST_GAME_CONFIG,
                                                        # The current turn is None, meaning the game has not yet
                                                        # started.
                                                        current_turn=None)
        self.mock_server.is_server = False
        gs: GameState = self.TEST_GAME_STATE
        # Remove the second player from game state and reset their settlements. We do this so that we can see a player
        # with the same attributes being added as a result of this event in the client's game state.
        joining_player: Player = gs.players.pop()
        joining_player.settlements = []
        self.mock_server.game_states_ref["local"] = gs
        gc: GameController = self.TEST_GAME_CONTROLLER
        # Simulate menu state as if the client is joining a game.
        gc.menu.joining_game = True
        gc.menu.viewing_lobbies = True
        gc.menu.viewing_local_lobbies = True
        gc.menu.setup_option = SetupOption.PLAYER_FACTION
        # Because we're joining as the second player, we use their identifier and faction in the event. We do this
        # because we're using the same test game clients as the other tests, meaning we need to use the values from
        # there, in addition to the fact that we want to see the client's player index change in game state.
        test_event: JoinEvent = JoinEvent(EventType.JOIN, self.TEST_IDENTIFIER_2, self.TEST_GAME_NAME,
                                          Faction.FRONTIERSMEN, lobby_details=test_lobby_details)

        # To begin with, the client should not be in a lobby, nor should they have determined their player index.
        self.assertIsNone(gc.menu.multiplayer_lobby)
        self.assertFalse(gs.player_idx)
        self.assertFalse(gs.located_player_idx)

        # Process our test event.
        self.request_handler.process_join_event(test_event, self.mock_socket)

        # The client should now be in the lobby from the test event.
        self.assertEqual(test_lobby_details, gc.menu.multiplayer_lobby)
        # They should also have determined their player index.
        self.assertEqual(1, gs.player_idx)
        self.assertTrue(gs.located_player_idx)
        # A new player representing the client should have been added to their game state.
        self.assertIn(joining_player, gs.players)
        # The menu should also have been updated to reflect the client joining.
        self.assertFalse(gc.menu.joining_game)
        self.assertFalse(gc.menu.viewing_lobbies)
        self.assertFalse(gc.menu.viewing_local_lobbies)
        self.assertEqual(SetupOption.START_GAME, gc.menu.setup_option)

    def test_process_join_event_client_already_in_lobby(self):
        """
        Ensure that game clients process join events correctly when the client is already in a lobby, and another client
        has just joined.
        """
        test_lobby_details: LobbyDetails = LobbyDetails(self.TEST_GAME_NAME,
                                                        # Just use our test game clients - we're simulating a situation
                                                        # where the client is the first player and the second player has
                                                        # just joined.
                                                        self.mock_server.game_clients_ref[self.TEST_GAME_NAME],
                                                        self.TEST_GAME_CONFIG,
                                                        # The current turn is None, meaning the game has not yet
                                                        # started.
                                                        current_turn=None)
        self.mock_server.is_server = False
        gs: GameState = self.TEST_GAME_STATE
        # Remove the second player from game state and reset their settlements. We do this so that we can see a player
        # with the same attributes being added as a result of this event in the client's game state.
        joining_player: Player = gs.players.pop()
        joining_player.settlements = []
        # Since the client is already in the lobby, naturally they would have located their player index.
        gs.located_player_idx = True
        self.mock_server.game_states_ref["local"] = gs
        gc: GameController = self.TEST_GAME_CONTROLLER
        # Simulate menu state as if the client is already in a lobby. This lobby is the same as the above one (which is
        # used for the test event), except it only has one player, reflecting the client's lobby prior to the new player
        # joining.
        gc.menu.multiplayer_lobby = LobbyDetails(self.TEST_GAME_NAME,
                                                 [test_lobby_details.current_players[0]],
                                                 self.TEST_GAME_CONFIG,
                                                 current_turn=None)
        # Because we're simulating the second player joining, we use their identifier and faction in the event. We do
        # this because we're using the same test game clients as the other tests, meaning we need to use the values from
        # there.
        test_event: JoinEvent = JoinEvent(EventType.JOIN, self.TEST_IDENTIFIER_2, self.TEST_GAME_NAME,
                                          Faction.FRONTIERSMEN, lobby_details=test_lobby_details)

        # Process our test event.
        self.request_handler.process_join_event(test_event, self.mock_socket)

        # The client's lobby should now have the players from the test event.
        self.assertEqual(test_lobby_details, gc.menu.multiplayer_lobby)
        # A new player representing the joining player should have been added to the client's game state.
        self.assertIn(joining_player, gs.players)

    @patch("source.networking.event_listener.save_stats_achievements")
    @patch("pyxel.mouse")
    def test_process_join_event_client_joining_game(self, pyxel_mouse_mock: MagicMock, achievements_mock: MagicMock):
        """
        Ensure that game clients process join events correctly when the client is joining an ongoing game.
        """
        test_lobby_details: LobbyDetails = LobbyDetails(self.TEST_GAME_NAME,
                                                        self.mock_server.game_clients_ref[self.TEST_GAME_NAME],
                                                        self.TEST_GAME_CONFIG,
                                                        current_turn=10)
        # The quad chunk we use for this test is just the same test quad over and over.
        test_quads_str: str = (minify_quad(self.TEST_QUAD) + ",") * 100
        # Some seen quads that will be sent to the client.
        test_seen_quads: List[Tuple[int, int]] = [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]
        self.mock_server.is_server = False
        gs: GameState = self.TEST_GAME_STATE
        # We need to keep the players separately here because they will be removed to simulate a real join situation.
        original_first_player: Player = gs.players[0]
        original_second_player: Player = gs.players[1]
        # Because we're using the same quad for the entire board, the settlement will actually have this quad rather
        # than TEST_QUAD_2.
        original_second_player.settlements[0].quads = [self.TEST_QUAD]
        # Make the second player returned to the client an AI - this is the player they will be taking control of.
        original_second_player.ai_playstyle = AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)
        # In a real join situation, the client won't have any players or heathens in their game state.
        gs.players = []
        gs.heathens = []
        # Manually change the until night and nighttime left values in game state so we can be sure that they were set
        # from the received packet, and didn't just happen to be randomly the same as the event.
        gs.until_night = 0
        gs.nighttime_left = 5
        self.mock_server.game_states_ref["local"] = gs
        gc: GameController = self.TEST_GAME_CONTROLLER
        gc.namer.remove_settlement_name = MagicMock()
        # Set an initial last turn time so we can see it being updated later.
        initial_last_turn_time: float = 0
        gc.last_turn_time = initial_last_turn_time
        gc.music_player.stop_menu_music = MagicMock()
        gc.music_player.play_game_music = MagicMock()
        # Because we're joining as the second player, we use their identifier and faction in the event. We do this
        # because we're using the same test game clients as the other tests, meaning we need to use the values from
        # there, in addition to the fact that we want to see the client's player index change in game state.
        test_event: JoinEvent = JoinEvent(EventType.JOIN, self.TEST_IDENTIFIER_2, self.TEST_GAME_NAME,
                                          Faction.FRONTIERSMEN, lobby_details=test_lobby_details,
                                          # The initial packet being sent is the first quad packet, containing game
                                          # configuration and quad data.
                                          until_night=3, nighttime_left=0, cfg=self.TEST_GAME_CONFIG,
                                          quad_chunk=test_quads_str, quad_chunk_idx=0)

        # To begin with, the client should not be in a lobby.
        self.assertIsNone(gc.menu.multiplayer_lobby)
        # They should also not have determined their player index.
        self.assertFalse(gs.player_idx)
        self.assertFalse(gs.located_player_idx)
        # Additionally, since they're not joining a game, there should be no game being loaded.
        self.assertIsNone(gc.menu.multiplayer_game_being_loaded)
        # Lastly, there should be no board.
        self.assertIsNone(gs.board)
        self.assertIsNone(gc.move_maker.board_ref)

        # Process our first test event.
        self.request_handler.process_join_event(test_event, self.mock_socket)

        # Not that it's currently being shown, but the client should now have the lobby from the test event on their
        # hidden menu.
        self.assertEqual(test_lobby_details, gc.menu.multiplayer_lobby)
        # They should also have determined their player index.
        self.assertEqual(1, gs.player_idx)
        self.assertTrue(gs.located_player_idx)
        # A new player representing the client should have been added to their game state - just without settlements or
        # the previously-held AI playstyle, since the client has taken control of them.
        joined_player: Player = deepcopy(original_second_player)
        joined_player.settlements = []
        joined_player.ai_playstyle = None
        self.assertIn(joined_player, gs.players)
        # Now the client should be loading a multiplayer game.
        self.assertIsNotNone(gc.menu.multiplayer_game_being_loaded)
        # Night details should have been set from the event.
        self.assertEqual(test_event.until_night, gs.until_night)
        self.assertEqual(test_event.nighttime_left, gs.nighttime_left)
        # The board should also have been initialised.
        self.assertIsNotNone(gs.board)
        self.assertEqual(gs.board, gc.move_maker.board_ref)
        # The first quad chunk should have been loaded.
        self.assertEqual(1, gc.menu.multiplayer_game_being_loaded.quad_chunks_loaded)
        # The game's turn should have been retrieved from the event.
        self.assertEqual(test_event.lobby_details.current_turn, gs.turn)
        # However since there are still many packets to come, the game should not have started.
        self.assertFalse(gs.game_started)

        # Simulate the client receiving the rest of the quad chunks. It doesn't make for a great board, but
        # for testing purposes, it doesn't matter that every quad will be the same.
        for i in range(1, 90):
            test_event.quad_chunk_idx = i
            self.request_handler.process_join_event(test_event, self.mock_socket)
        # All quad chunks should now be loaded.
        self.assertEqual(90, gc.menu.multiplayer_game_being_loaded.quad_chunks_loaded)
        # We can even make sure that the correct quad was assigned for all of the board's quads.
        for i in range(90):
            for j in range(100):
                # We do have to mock the location however, as that was the same in the quad chunk.
                self.TEST_QUAD.location = j, i
                self.assertEqual(self.TEST_QUAD, gs.board.quads[i][j])

        # Reset the test event for the player chunks.
        test_event.quad_chunk = None
        test_event.quad_chunk_idx = None

        # Process the next event with the first player's details.
        test_event.player_chunk = minify_player(original_first_player)
        test_event.player_chunk_idx = 0
        self.request_handler.process_join_event(test_event, self.mock_socket)
        # The first player should have been loaded in correctly, with their settlement name also being removed.
        self.assertEqual(original_first_player, gs.players[0])
        gc.namer.remove_settlement_name.assert_called_with(original_first_player.settlements[0].name,
                                                           original_first_player.settlements[0].quads[0].biome)
        # One player should have been loaded, naturally.
        self.assertEqual(1, gc.menu.multiplayer_game_being_loaded.players_loaded)
        # The game should still not have started, as the other player, plus seen quads and heathens, are still to come.
        self.assertFalse(gs.game_started)

        # Process the next event with the second player's details.
        test_event.player_chunk = minify_player(original_second_player)
        test_event.player_chunk_idx = 1
        self.request_handler.process_join_event(test_event, self.mock_socket)
        # The second player should have been loaded in correctly, with their settlement name also being removed.
        self.assertEqual(original_second_player, gs.players[1])
        gc.namer.remove_settlement_name.assert_called_with(original_second_player.settlements[0].name,
                                                           original_second_player.settlements[0].quads[0].biome)
        # Now both players should have been loaded.
        self.assertEqual(2, gc.menu.multiplayer_game_being_loaded.players_loaded)
        # The game should still not have started, as seen quads and heathens are still to come.
        self.assertFalse(gs.game_started)

        # Reset the test event for the seen quads chunks - noting that the player_chunk_idx is still used to identify
        # which player the seen quads belong to.
        test_event.player_chunk = None

        # Process the next event with the seen quads for the first player. Note that the total quads seen is simply
        # twice the test seen quads list, as for testing purposes, both players have the same seen quads.
        test_event.player_chunk_idx = 0
        test_event.quads_seen_chunk = minify_quads_seen(set(test_seen_quads))
        test_event.total_quads_seen = len(test_seen_quads) * 2
        self.request_handler.process_join_event(test_event, self.mock_socket)
        # The seen quads for the first player should have been loaded in correctly, with the multiplayer game being
        # loaded being updated as well.
        self.assertEqual(test_event.total_quads_seen, gc.menu.multiplayer_game_being_loaded.total_quads_seen)
        self.assertEqual(set(test_seen_quads), gs.players[0].quads_seen)
        self.assertEqual(len(test_seen_quads), gc.menu.multiplayer_game_being_loaded.quads_seen_loaded)
        # The game should still not have started, as the seen quads for the other player, and heathens, are still to
        # come.
        self.assertFalse(gs.game_started)

        # Process the next event with the seen quads for the second player. Note that the actual chunk and the total are
        # unchanged for this event, for reasons described above.
        test_event.player_chunk_idx = 1
        self.request_handler.process_join_event(test_event, self.mock_socket)
        # The seen quads for the second player should have been loaded in correctly, with the multiplayer game being
        # loaded being updated as well.
        self.assertEqual(set(test_seen_quads), gs.players[1].quads_seen)
        self.assertEqual(len(test_seen_quads) * 2, gc.menu.multiplayer_game_being_loaded.quads_seen_loaded)
        # The game should still not have started, as the heathens are still to come.
        self.assertFalse(gs.game_started)

        # Reset the test event for the heathen chunk.
        test_event.player_chunk_idx = None
        test_event.quads_seen_chunk = None
        test_event.total_quads_seen = None

        # Process the final event with the heathens in the game.
        test_event.heathens_chunk = minify_heathens([self.TEST_HEATHEN])
        test_event.total_heathens = 1
        self.request_handler.process_join_event(test_event, self.mock_socket)
        # The heathens should have been loaded in correctly.
        self.assertListEqual([self.TEST_HEATHEN], gs.heathens)
        # Note that we can't test the total heathens or heathens loaded attributes here because the game being loaded is
        # made None once it's finished loading.

        # Finally, the game should have started, with the client having entered the game.
        pyxel_mouse_mock.assert_called_with(visible=True)
        self.assertGreater(gc.last_turn_time, initial_last_turn_time)
        self.assertTrue(gs.game_started)
        self.assertFalse(gs.on_menu)
        achievements_mock.assert_called_with(gs, faction_to_add=test_event.player_faction)
        # The test settlement is near the top-left of the board, so we do our best to centre on it.
        self.assertTupleEqual((-1, -1), gs.map_pos)
        # Since the seen quads will have been loaded, we need to add that in here before validating against the current
        # player in the overlay.
        original_second_player.quads_seen = set(test_seen_quads)
        self.assertEqual(original_second_player, gs.board.overlay.current_player)
        # Two settlements - one for each player. This differs from init events in that init events will add an extra one
        # to the count in anticipation of the player founding a new settlement. For join events however, the joining
        # client is not able to found a new settlement when they join, since they'll already have one (or more).
        self.assertEqual(2, gs.board.overlay.total_settlement_count)
        gc.music_player.stop_menu_music.assert_called()
        gc.music_player.play_game_music.assert_called()
        # The game being loaded on the menu should now also have been reset.
        self.assertIsNone(gc.menu.multiplayer_game_being_loaded)

    def test_process_join_event_client_already_in_game(self):
        """
        Ensure that game clients process join events correctly when the client is in an ongoing game and another client
        joins.
        """
        test_lobby_details: LobbyDetails = LobbyDetails(self.TEST_GAME_NAME,
                                                        self.mock_server.game_clients_ref[self.TEST_GAME_NAME],
                                                        self.TEST_GAME_CONFIG,
                                                        current_turn=10)
        self.mock_server.is_server = False
        gs: GameState = self.TEST_GAME_STATE
        # For this test, we actually need an initialised board.
        gs.board = Board(self.TEST_GAME_CONFIG, Namer(), {})
        gs.board.overlay.toggle_player_change = MagicMock()
        # Make the second player in the game an AI - this is the player the other client will be taking control of.
        gs.players[1].ai_playstyle = AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)
        gs.game_started = True
        self.mock_server.game_states_ref["local"] = gs
        gc: GameController = self.TEST_GAME_CONTROLLER
        # Simulate menu state as if the client was already in a lobby prior to the game starting. This lobby is the same
        # as the above one (which is used for the test event), except it only has one player, reflecting the client's
        # lobby before the game started.
        gc.menu.multiplayer_lobby = LobbyDetails(self.TEST_GAME_NAME,
                                                 [test_lobby_details.current_players[0]],
                                                 self.TEST_GAME_CONFIG,
                                                 current_turn=10)
        # Because the second player is joining the client's game, we use their identifier and faction in the event. We
        # do this because we're using the same test game clients as the other tests, meaning we need to use the values
        # from there.
        test_event: JoinEvent = JoinEvent(EventType.JOIN, self.TEST_IDENTIFIER_2, self.TEST_GAME_NAME,
                                          Faction.FRONTIERSMEN, lobby_details=test_lobby_details)

        # Process our test event.
        self.request_handler.process_join_event(test_event, self.mock_socket)

        # The client's lobby should now have the players from the test event.
        self.assertEqual(test_lobby_details, gc.menu.multiplayer_lobby)
        # The player the new client took control of should no longer have an AI playstyle.
        self.assertIsNone(gs.players[1].ai_playstyle)
        # The appropriate overlay change should also have occurred to alert the client that another player has joined.
        gs.board.overlay.toggle_player_change.assert_called_with(gs.players[1], changed_player_is_leaving=False)

    def test_process_register_event_server(self):
        """
        Ensure that register events are correctly processed by the game server.
        """
        self.mock_server.is_server = True
        # Clear our clients so we can have a clean slate for our test.
        self.mock_server.clients_ref = {}
        test_event: RegisterEvent = RegisterEvent(EventType.REGISTER, self.TEST_IDENTIFIER, port=9876)
        # Process our test event.
        self.request_handler.process_register_event(test_event, self.mock_socket)
        # There should now be a client with the expected identifier and port.
        self.assertTupleEqual((self.request_handler.client_address[0], test_event.port),
                              self.mock_server.clients_ref[test_event.identifier])
        # Additionally, an event should have been dispatched in response to the client.
        self.mock_socket.sendto.assert_called_with(json.dumps(test_event,
                                                              separators=(",", ":"),
                                                              cls=SaveEncoder).encode(),
                                                   (self.request_handler.client_address[0], test_event.port))

    def test_process_register_event_client(self):
        """
        Ensure that register events are correctly processed by game clients.
        """
        test_event: RegisterEvent = RegisterEvent(EventType.REGISTER, self.TEST_IDENTIFIER, port=9876)
        test_local_server_host: str = "127.0.0.1"
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # Process our test event, simulating a response from the global game server.
        self.request_handler.client_address = (GLOBAL_SERVER_HOST,)
        self.request_handler.process_register_event(test_event, self.mock_socket)

        # Because it was a response from the global game server, it should have been ignored and there should be no
        # local event dispatcher.
        self.assertFalse(DispatcherKind.LOCAL in self.TEST_GAME_STATE.event_dispatchers)
        self.assertFalse(self.mock_server.game_controller_ref.menu.has_local_dispatcher)

        # Now process our test event again, but this time simulate a response from a local game server.
        self.request_handler.client_address = (test_local_server_host,)
        self.request_handler.process_register_event(test_event, self.mock_socket)

        # This time, we expect a local dispatcher to have been added.
        self.assertTrue(DispatcherKind.LOCAL in self.TEST_GAME_STATE.event_dispatchers)
        self.assertEqual(test_local_server_host, self.TEST_GAME_STATE.event_dispatchers[DispatcherKind.LOCAL].host)
        self.assertTrue(self.mock_server.game_controller_ref.menu.has_local_dispatcher)

    @patch.object(GameState, "__hash__")
    @patch("source.networking.event_listener.save_game")
    @patch("random.seed")
    def test_process_end_turn_event_server(self,
                                           random_seed_mock: MagicMock,
                                           save_game_mock: MagicMock,
                                           game_state_hash_mock: MagicMock):
        """
        Ensure that the game server correctly processes end turn events.
        """
        # Mock out the actual hash value of the game state to avoid having to account for the inherent randomness of the
        # game state between test runs.
        test_game_state_hash: int = 1234
        game_state_hash_mock.return_value = test_game_state_hash
        # For this test, we actually need an initialised board.
        self.TEST_GAME_STATE.board = Board(self.TEST_GAME_CONFIG, Namer(), {})
        # Reduce the test heathen's stamina and health so we can see them both being replenished.
        self.TEST_HEATHEN.remaining_stamina = 0
        self.TEST_HEATHEN.health = 1
        # Mock out all the more complicated processing methods - testing their logic isn't the point of this test.
        self.TEST_GAME_STATE.process_player = MagicMock()
        self.TEST_GAME_STATE.process_climatic_effects = MagicMock()
        self.TEST_GAME_STATE.process_heathens = MagicMock()
        self.TEST_GAME_STATE.process_ais = MagicMock()
        # We have to make sure the main player isn't the only one with a settlement, which would trigger an Elimination
        # victory.
        self.TEST_GAME_STATE.players[1].settlements = [self.TEST_SETTLEMENT_2]
        # Set the turn to 5 so that a heathen will be spawned.
        self.TEST_GAME_STATE.turn = 5
        # Simulate a situation in which one player has already ended their turn.
        self.TEST_GAME_STATE.ready_players = {self.TEST_IDENTIFIER_2}
        test_event: EndTurnEvent = EndTurnEvent(EventType.END_TURN, self.TEST_IDENTIFIER, self.TEST_GAME_NAME)
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE
        # We need a MoveMaker for this test too, since AI players are processed.
        test_movemaker: MoveMaker = MoveMaker(Namer())
        self.mock_server.move_makers_ref[self.TEST_GAME_NAME] = test_movemaker

        # Process our test event.
        self.request_handler.process_end_turn_event(test_event, self.mock_socket)

        # We expect the random number generator to have been seeded with the turn we specified earlier, for
        # synchronisation purposes.
        random_seed_mock.assert_called_with(5)
        # We expect each player to be processed.
        self.assertEqual(len(self.TEST_GAME_STATE.players), self.TEST_GAME_STATE.process_player.call_count)
        # We also expect a new heathen to be spawned, and for all existing heathens to have their stamina reset and
        # their health partly replenished.
        self.assertEqual(2, len(self.TEST_GAME_STATE.heathens))
        self.assertTrue(self.TEST_HEATHEN.remaining_stamina)
        self.assertGreater(self.TEST_HEATHEN.health, 1)
        # The turn should also be incremented and climatic effects processed, since our test game configuration has them
        # enabled.
        self.assertEqual(6, self.TEST_GAME_STATE.turn)
        self.TEST_GAME_STATE.process_climatic_effects.assert_called_with(reseed_random=False)
        # Since no victory was achieved, we expect the game to have been autosaved, with heathens and AI players also
        # processed.
        save_game_mock.assert_called_with(self.TEST_GAME_STATE, auto=True)
        self.TEST_GAME_STATE.process_heathens.assert_called()
        self.TEST_GAME_STATE.process_ais.assert_called_with(test_movemaker)
        # We also expect the game state hash to have been set to our mocked hash value from the server's side, to be
        # used for synchronisation purposes by clients.
        self.assertEqual(test_game_state_hash, test_event.game_state_hash)
        # We also expect all game clients to have been alerted that the turn has ended, not just clients other than the
        # one that dispatched the event.
        self.assertEqual(2, len(self.mock_socket.sendto.mock_calls))
        # The server's ready players should also have been reset, since a new turn has begun.
        self.assertFalse(self.TEST_GAME_STATE.ready_players)

    @patch.object(GameState, "__hash__")
    @patch("source.networking.event_listener.save_stats_achievements")
    @patch("random.seed")
    def test_process_end_turn_event_client_victory(self,
                                                   random_seed_mock: MagicMock,
                                                   achievements_mock: MagicMock,
                                                   game_state_hash_mock: MagicMock):
        """
        Ensure that game clients correctly process end turn events where the client has achieved a victory.
        """
        # For this test, we actually need an initialised board.
        self.TEST_GAME_STATE.board = Board(self.TEST_GAME_CONFIG, Namer(), {})
        self.TEST_GAME_STATE.board.overlay.remove_warning_if_possible = MagicMock()
        self.TEST_GAME_STATE.board.overlay.toggle_victory = MagicMock()
        self.TEST_GAME_STATE.board.overlay.toggle_ach_notif = MagicMock()
        self.TEST_GAME_STATE.board.overlay.toggle_desync = MagicMock()
        # If the client is waiting for the server to end the turn, then they will be waiting for other players.
        self.TEST_GAME_STATE.board.waiting_for_other_players = True
        # Mock that an achievement is returned when the client wins the game.
        achievements_mock.return_value = [ACHIEVEMENTS[0]]
        # Reduce the test heathen's stamina and health so we can see them both being replenished.
        self.TEST_HEATHEN.remaining_stamina = 0
        self.TEST_HEATHEN.health = 1
        # Mock out all the more complicated processing methods - testing their logic isn't the point of this test.
        self.TEST_GAME_STATE.process_player = MagicMock()
        self.TEST_GAME_STATE.process_climatic_effects = MagicMock()
        # Set the turn to 5 so that a heathen will be spawned.
        self.TEST_GAME_STATE.turn = 5
        # Remove the other player's settlement to trigger an elimination victory.
        self.TEST_GAME_STATE.players[1].settlements = []
        # Mock out the actual hash value of the game state to avoid having to account for the inherent randomness of the
        # game state between test runs.
        test_game_state_hash: int = 1234
        game_state_hash_mock.return_value = test_game_state_hash
        # The server will have tacked on the hash of its game state in its forwarded packet.
        test_event: EndTurnEvent = EndTurnEvent(EventType.END_TURN, self.TEST_IDENTIFIER, self.TEST_GAME_NAME,
                                                game_state_hash=test_game_state_hash)
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # Process our test event.
        self.request_handler.process_end_turn_event(test_event, self.mock_socket)

        # We expect the random number generator to have been seeded with the turn we specified earlier, for
        # synchronisation purposes.
        random_seed_mock.assert_called_with(5)
        # We expect each player to be processed.
        self.assertEqual(len(self.TEST_GAME_STATE.players), self.TEST_GAME_STATE.process_player.call_count)
        # We also expect a new heathen to be spawned, and for all existing heathens to have their stamina reset and
        # their health partly replenished.
        self.assertEqual(2, len(self.TEST_GAME_STATE.heathens))
        self.assertTrue(self.TEST_HEATHEN.remaining_stamina)
        self.assertGreater(self.TEST_HEATHEN.health, 1)
        self.TEST_GAME_STATE.board.overlay.remove_warning_if_possible.assert_called()
        # The turn should also be incremented and climatic effects processed, since our test game configuration has them
        # enabled.
        self.assertEqual(6, self.TEST_GAME_STATE.turn)
        self.TEST_GAME_STATE.process_climatic_effects.assert_called_with(reseed_random=False)
        # We expect a victory for the first player to have been triggered, with the relevant overlay updates occurring.
        self.TEST_GAME_STATE.board.overlay.toggle_victory.assert_called_with(Victory(self.TEST_GAME_STATE.players[0],
                                                                                     VictoryType.ELIMINATION))
        self.TEST_GAME_STATE.board.overlay.toggle_ach_notif.assert_called_with([ACHIEVEMENTS[0]])
        # Since the hash received by the client in the server's packet is identical to the client's one, the desync
        # overlay should not be displayed.
        self.TEST_GAME_STATE.board.overlay.toggle_desync.assert_not_called()
        # The client should now also no longer be waiting for other players.
        self.assertFalse(self.TEST_GAME_STATE.board.waiting_for_other_players)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

    @patch.object(GameState, "__hash__")
    @patch("source.networking.event_listener.save_stats_achievements")
    @patch("random.seed")
    def test_process_end_turn_event_client_defeat(self,
                                                  random_seed_mock: MagicMock,
                                                  achievements_mock: MagicMock,
                                                  game_state_hash_mock: MagicMock):
        """
        Ensure that game clients correctly process end turn events where another client has achieved a victory.
        """
        # For this test, we actually need an initialised board.
        self.TEST_GAME_STATE.board = Board(self.TEST_GAME_CONFIG, Namer(), {})
        self.TEST_GAME_STATE.board.overlay.remove_warning_if_possible = MagicMock()
        self.TEST_GAME_STATE.board.overlay.toggle_victory = MagicMock()
        self.TEST_GAME_STATE.board.overlay.toggle_ach_notif = MagicMock()
        self.TEST_GAME_STATE.board.overlay.toggle_desync = MagicMock()
        # If the client is waiting for the server to end the turn, then they will be waiting for other players.
        self.TEST_GAME_STATE.board.waiting_for_other_players = True
        # Mock that an achievement is returned when the client is defeated.
        achievements_mock.return_value = [ACHIEVEMENTS[-3]]
        # Reduce the test heathen's stamina and health so we can see them both being replenished.
        self.TEST_HEATHEN.remaining_stamina = 0
        self.TEST_HEATHEN.health = 1
        # Mock out all the more complicated processing methods - testing their logic isn't the point of this test.
        self.TEST_GAME_STATE.process_player = MagicMock()
        self.TEST_GAME_STATE.process_climatic_effects = MagicMock()
        # Set the turn to 5 so that a heathen will be spawned.
        self.TEST_GAME_STATE.turn = 5
        # Give the other player sufficient accumulated wealth to trigger an affluence victory.
        self.TEST_GAME_STATE.players[1].accumulated_wealth = 100000
        # Mock out the actual hash value of the game state to avoid having to account for the inherent randomness of the
        # game state between test runs.
        test_game_state_hash: int = 1234
        game_state_hash_mock.return_value = test_game_state_hash
        # The server will have tacked on the hash of its game state in its forwarded packet.
        test_event: EndTurnEvent = EndTurnEvent(EventType.END_TURN, self.TEST_IDENTIFIER, self.TEST_GAME_NAME,
                                                game_state_hash=test_game_state_hash)
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # Process our test event.
        self.request_handler.process_end_turn_event(test_event, self.mock_socket)

        # We expect the random number generator to have been seeded with the turn we specified earlier, for
        # synchronisation purposes.
        random_seed_mock.assert_called_with(5)
        # We expect each player to be processed.
        self.assertEqual(len(self.TEST_GAME_STATE.players), self.TEST_GAME_STATE.process_player.call_count)
        # We also expect a new heathen to be spawned, and for all existing heathens to have their stamina reset and
        # their health partly replenished.
        self.assertEqual(2, len(self.TEST_GAME_STATE.heathens))
        self.assertTrue(self.TEST_HEATHEN.remaining_stamina)
        self.assertGreater(self.TEST_HEATHEN.health, 1)
        self.TEST_GAME_STATE.board.overlay.remove_warning_if_possible.assert_called()
        # The turn should also be incremented and climatic effects processed, since our test game configuration has them
        # enabled.
        self.assertEqual(6, self.TEST_GAME_STATE.turn)
        self.TEST_GAME_STATE.process_climatic_effects.assert_called_with(reseed_random=False)
        # We expect a victory for the second player to have been triggered, with the relevant overlay updates occurring.
        self.TEST_GAME_STATE.board.overlay.toggle_victory.assert_called_with(Victory(self.TEST_GAME_STATE.players[1],
                                                                                     VictoryType.AFFLUENCE))
        self.TEST_GAME_STATE.board.overlay.toggle_ach_notif.assert_called_with([ACHIEVEMENTS[-3]])
        # Since the hash received by the client in the server's packet is identical to the client's one, the desync
        # overlay should not be displayed.
        self.TEST_GAME_STATE.board.overlay.toggle_desync.assert_not_called()
        # The client should now also no longer be waiting for other players.
        self.assertFalse(self.TEST_GAME_STATE.board.waiting_for_other_players)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

    @patch.object(GameState, "__hash__")
    @patch("source.networking.event_listener.save_stats_achievements")
    @patch("random.seed")
    def test_process_end_turn_event_client_no_victory(self,
                                                      random_seed_mock: MagicMock,
                                                      achievements_mock: MagicMock,
                                                      game_state_hash_mock: MagicMock):
        """
        Ensure that game clients correctly process end turn events where no victory is achieved.
        """
        # For this test, we actually need an initialised board.
        self.TEST_GAME_STATE.board = Board(self.TEST_GAME_CONFIG, Namer(), {})
        self.TEST_GAME_STATE.board.overlay.remove_warning_if_possible = MagicMock()
        self.TEST_GAME_STATE.board.overlay.toggle_ach_notif = MagicMock()
        self.TEST_GAME_STATE.board.overlay.toggle_desync = MagicMock()
        # If the client is waiting for the server to end the turn, then they will be waiting for other players.
        self.TEST_GAME_STATE.board.waiting_for_other_players = True
        # Mock that an achievement is returned when the next turn begins.
        achievements_mock.return_value = [ACHIEVEMENTS[2]]
        # Reduce the test heathen's stamina and health so we can see them both being replenished.
        self.TEST_HEATHEN.remaining_stamina = 0
        self.TEST_HEATHEN.health = 1
        # Mock out all the more complicated processing methods - testing their logic isn't the point of this test.
        self.TEST_GAME_STATE.process_player = MagicMock()
        self.TEST_GAME_STATE.process_climatic_effects = MagicMock()
        self.TEST_GAME_STATE.process_heathens = MagicMock()
        self.TEST_GAME_STATE.process_ais = MagicMock()
        # Set the turn to 5 so that a heathen will be spawned.
        self.TEST_GAME_STATE.turn = 5
        # Set an initial last turn time so we can see it being updated later.
        initial_last_turn_time: float = 0
        self.TEST_GAME_CONTROLLER.last_turn_time = initial_last_turn_time
        # Mock out the actual hash value of the game state to avoid having to account for the inherent randomness of the
        # game state between test runs.
        test_game_state_hash: int = 1234
        game_state_hash_mock.return_value = test_game_state_hash
        # The server will have tacked on the hash of its game state in its forwarded packet.
        test_event: EndTurnEvent = EndTurnEvent(EventType.END_TURN, self.TEST_IDENTIFIER, self.TEST_GAME_NAME,
                                                game_state_hash=test_game_state_hash)
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # Process our test event.
        self.request_handler.process_end_turn_event(test_event, self.mock_socket)

        # We expect the random number generator to have been seeded with the turn we specified earlier, for
        # synchronisation purposes.
        random_seed_mock.assert_called_with(5)
        # We expect each player to be processed.
        self.assertEqual(len(self.TEST_GAME_STATE.players), self.TEST_GAME_STATE.process_player.call_count)
        # We also expect a new heathen to be spawned, and for all existing heathens to have their stamina reset and
        # their health partly replenished.
        self.assertEqual(2, len(self.TEST_GAME_STATE.heathens))
        self.assertTrue(self.TEST_HEATHEN.remaining_stamina)
        self.assertGreater(self.TEST_HEATHEN.health, 1)
        self.TEST_GAME_STATE.board.overlay.remove_warning_if_possible.assert_called()
        # The turn should also be incremented and climatic effects processed, since our test game configuration has them
        # enabled.
        self.assertEqual(6, self.TEST_GAME_STATE.turn)
        self.TEST_GAME_STATE.process_climatic_effects.assert_called_with(reseed_random=False)
        self.assertGreater(self.TEST_GAME_CONTROLLER.last_turn_time, initial_last_turn_time)
        # The relevant overlay related updates should have occurred.
        self.TEST_GAME_STATE.board.overlay.toggle_ach_notif.assert_called_with([ACHIEVEMENTS[2]])
        self.assertEqual(2, self.TEST_GAME_STATE.board.overlay.total_settlement_count)
        # Since the game is continuing, we expect the turns for heathens and AI players to have been processed.
        self.TEST_GAME_STATE.process_heathens.assert_called()
        self.TEST_GAME_STATE.process_ais.assert_called_with(self.TEST_GAME_CONTROLLER.move_maker)
        # Since the hash received by the client in the server's packet is identical to the client's one, the desync
        # overlay should not be displayed.
        self.TEST_GAME_STATE.board.overlay.toggle_desync.assert_not_called()
        # The client should now also no longer be waiting for other players.
        self.assertFalse(self.TEST_GAME_STATE.board.waiting_for_other_players)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

    @patch.object(GameState, "__hash__")
    @patch("source.networking.event_listener.save_stats_achievements")
    @patch("random.seed")
    def test_process_end_turn_event_client_no_victory_desync(self,
                                                             random_seed_mock: MagicMock,
                                                             achievements_mock: MagicMock,
                                                             game_state_hash_mock: MagicMock):
        """
        Ensure that game clients correctly process end turn events where no victory is achieved, and the client has lost
        sync with the server.
        """
        # For this test, we actually need an initialised board.
        self.TEST_GAME_STATE.board = Board(self.TEST_GAME_CONFIG, Namer(), {})
        self.TEST_GAME_STATE.board.overlay.remove_warning_if_possible = MagicMock()
        self.TEST_GAME_STATE.board.overlay.toggle_ach_notif = MagicMock()
        self.TEST_GAME_STATE.board.overlay.toggle_desync = MagicMock()
        # If the client is waiting for the server to end the turn, then they will be waiting for other players.
        self.TEST_GAME_STATE.board.waiting_for_other_players = True
        # Mock that an achievement is returned when the next turn begins.
        achievements_mock.return_value = [ACHIEVEMENTS[2]]
        # Reduce the test heathen's stamina and health so we can see them both being replenished.
        self.TEST_HEATHEN.remaining_stamina = 0
        self.TEST_HEATHEN.health = 1
        # Mock out all the more complicated processing methods - testing their logic isn't the point of this test.
        self.TEST_GAME_STATE.process_player = MagicMock()
        self.TEST_GAME_STATE.process_climatic_effects = MagicMock()
        self.TEST_GAME_STATE.process_heathens = MagicMock()
        self.TEST_GAME_STATE.process_ais = MagicMock()
        # Set the turn to 5 so that a heathen will be spawned.
        self.TEST_GAME_STATE.turn = 5
        # Set an initial last turn time so we can see it being updated later.
        initial_last_turn_time: float = 0
        self.TEST_GAME_CONTROLLER.last_turn_time = initial_last_turn_time
        # Mock out the actual hash value of the game state to avoid having to account for the inherent randomness of the
        # game state between test runs.
        test_game_state_hash: int = 1234
        game_state_hash_mock.return_value = test_game_state_hash
        # The server will have tacked on the hash of its game state in its forwarded packet. For this test, we want the
        # client and the server to be out of sync, so we just subtract one from the simulated server hash.
        test_event: EndTurnEvent = EndTurnEvent(EventType.END_TURN, self.TEST_IDENTIFIER, self.TEST_GAME_NAME,
                                                game_state_hash=test_game_state_hash - 1)
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE

        # Process our test event.
        self.request_handler.process_end_turn_event(test_event, self.mock_socket)

        # We expect the random number generator to have been seeded with the turn we specified earlier, for
        # synchronisation purposes.
        random_seed_mock.assert_called_with(5)
        # We expect each player to be processed.
        self.assertEqual(len(self.TEST_GAME_STATE.players), self.TEST_GAME_STATE.process_player.call_count)
        # We also expect a new heathen to be spawned, and for all existing heathens to have their stamina reset and
        # their health partly replenished.
        self.assertEqual(2, len(self.TEST_GAME_STATE.heathens))
        self.assertTrue(self.TEST_HEATHEN.remaining_stamina)
        self.assertGreater(self.TEST_HEATHEN.health, 1)
        self.TEST_GAME_STATE.board.overlay.remove_warning_if_possible.assert_called()
        # The turn should also be incremented and climatic effects processed, since our test game configuration has them
        # enabled.
        self.assertEqual(6, self.TEST_GAME_STATE.turn)
        self.TEST_GAME_STATE.process_climatic_effects.assert_called_with(reseed_random=False)
        self.assertGreater(self.TEST_GAME_CONTROLLER.last_turn_time, initial_last_turn_time)
        # The relevant overlay related updates should have occurred.
        self.TEST_GAME_STATE.board.overlay.toggle_ach_notif.assert_called_with([ACHIEVEMENTS[2]])
        self.assertEqual(2, self.TEST_GAME_STATE.board.overlay.total_settlement_count)
        # Since the game is continuing, we expect the turns for heathens and AI players to have been processed.
        self.TEST_GAME_STATE.process_heathens.assert_called()
        self.TEST_GAME_STATE.process_ais.assert_called_with(self.TEST_GAME_CONTROLLER.move_maker)
        # Since the hash received by the client in the server's packet is one off its own generated game state hash, the
        # desync overlay should be displayed.
        self.TEST_GAME_STATE.board.overlay.toggle_desync.assert_called()
        # The client should now also no longer be waiting for other players.
        self.assertFalse(self.TEST_GAME_STATE.board.waiting_for_other_players)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

    def test_process_unready_event(self):
        """
        Ensure that unready events are correctly processed by the game server.
        """
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE
        gs: GameState = self.mock_server.game_states_ref[self.TEST_GAME_NAME]
        gs.ready_players = {self.TEST_IDENTIFIER}
        test_event: UnreadyEvent = UnreadyEvent(EventType.UNREADY, self.TEST_IDENTIFIER, self.TEST_GAME_NAME)
        # Process our test event.
        self.request_handler.process_unready_event(test_event)
        # The corresponding identifier in the game state's ready players should have been removed.
        self.assertFalse(gs.ready_players)

    @patch("random.choice")
    def test_process_autofill_event_server(self, random_choice_mock: MagicMock):
        """
        Ensure that the game server correctly processes autofill events.
        """
        test_event: AutofillEvent = AutofillEvent(EventType.AUTOFILL, self.TEST_IDENTIFIER, self.TEST_GAME_NAME)
        self.mock_server.is_server = True
        # Use a different GameConfig that allows for three players.
        three_player_conf: GameConfig = \
            GameConfig(3, Faction.AGRICULTURISTS, True, True, True, MultiplayerStatus.GLOBAL)
        self.mock_server.lobbies_ref[self.TEST_GAME_NAME] = three_player_conf
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE
        # We need to pre-determine the AI player's details so we can use them in our random mock.
        ai_player_name: str = "Mr. Roboto"
        ai_faction: Faction = Faction.FUNDAMENTALISTS
        ai_playstyle: AIPlaystyle = AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)
        # There are up to six calls to random.choice() when processing autofill events, as the server attempts to assign
        # the AI player a name, a faction, and then an AI playstyle. To account for all logic branches, on the first
        # attempt for both the name and faction, we return one already in use by a player currently in the game. Lastly,
        # we return a valid AI playstyle.
        random_choice_mock.side_effect = [self.TEST_GAME_STATE.players[0].name, ai_player_name,
                                          self.TEST_GAME_STATE.players[0].faction, ai_faction,
                                          ai_playstyle.attacking, ai_playstyle.expansion]
        # When created, we expect our AI player to have the following attributes.
        expected_ai_player: Player = Player(ai_player_name, ai_faction, FACTION_COLOURS[ai_faction],
                                            ai_playstyle=ai_playstyle)

        # Process our test event.
        self.request_handler.process_autofill_event(test_event, self.mock_socket)

        # There should now be a third player in the game - the AI player just generated.
        self.assertEqual(3, len(self.TEST_GAME_STATE.players))
        self.assertEqual(expected_ai_player, self.TEST_GAME_STATE.players[2])
        self.assertListEqual(self.TEST_GAME_STATE.players, test_event.players)
        # We also expect these details to have been forwarded to all game clients, not just clients other than the one
        # that dispatched the event.
        self.assertEqual(2, len(self.mock_socket.sendto.mock_calls))

    def test_process_autofill_event_client(self):
        """
        Ensure that game clients correctly process autofill events.
        """
        ai_player: Player = Player("Mr. Roboto", Faction.FUNDAMENTALISTS, FACTION_COLOURS[Faction.FUNDAMENTALISTS],
                                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL))
        # Since we need to maintain two parallel game states, we create a new list inline for the event players, and
        # leave the ones in test game state untouched.
        test_event: AutofillEvent = AutofillEvent(EventType.AUTOFILL, self.TEST_IDENTIFIER, self.TEST_GAME_NAME,
                                                  players=self.TEST_GAME_STATE.players + [ai_player])
        self.mock_server.is_server = False
        self.mock_server.game_states_ref["local"] = self.TEST_GAME_STATE
        # Use a different GameConfig that allows for three players.
        three_player_conf: GameConfig = \
            GameConfig(3, Faction.AGRICULTURISTS, True, True, True, MultiplayerStatus.GLOBAL)
        menu: Menu = self.mock_server.game_controller_ref.menu
        menu.multiplayer_lobby = \
            LobbyDetails("Cool", self.mock_server.game_clients_ref[self.TEST_GAME_NAME], three_player_conf, None)

        # Process our test event.
        self.request_handler.process_autofill_event(test_event, self.mock_socket)

        # The client's lobby should now have three players, with the third representative of the autofilled AI player.
        self.assertEqual(3, len(menu.multiplayer_lobby.current_players))
        self.assertEqual(PlayerDetails(ai_player.name, ai_player.faction, id=None),
                         menu.multiplayer_lobby.current_players[2])
        # The AI player should also have been added to the game state, in accordance with the event.
        self.assertListEqual(test_event.players, self.TEST_GAME_STATE.players)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

    @patch("source.networking.event_listener.save_game")
    def test_process_save_event(self, save_game_mock: MagicMock):
        """
        Ensure that save events are correctly processed by the game server.
        """
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE
        test_event: SaveEvent = SaveEvent(EventType.SAVE, self.TEST_IDENTIFIER, self.TEST_GAME_NAME)
        self.request_handler.process_save_event(test_event)
        save_game_mock.assert_called_with(self.TEST_GAME_STATE)

    @patch("source.networking.event_listener.get_saves")
    def test_process_query_saves_event_server(self, get_saves_mock: MagicMock):
        """
        Ensure that the game server correctly processes query saves events.
        """
        test_saves: List[str] = ["abc", "123", "!@#"]
        get_saves_mock.return_value = test_saves
        test_event: QuerySavesEvent = QuerySavesEvent(EventType.QUERY_SAVES, self.TEST_IDENTIFIER)
        self.mock_server.is_server = True

        # Process our test event.
        self.request_handler.process_query_saves_event(test_event, self.mock_socket)

        # The event should now be populated with saves for the client to choose from.
        self.assertEqual(test_saves, test_event.saves)
        # We also expect the server to have sent a packet containing a JSON representation of the event to the client
        # that originally dispatched the query saves event.
        self.mock_socket.sendto.assert_called_with(json.dumps(test_event, cls=SaveEncoder).encode(),
                                                   (self.TEST_HOST, self.TEST_PORT))

    def test_process_query_saves_event_client(self):
        """
        Ensure that game clients correctly process query saves events.
        """
        test_event: QuerySavesEvent = QuerySavesEvent(EventType.QUERY_SAVES, self.TEST_IDENTIFIER,
                                                      saves=["abc", "123"])
        self.mock_server.is_server = False

        # The client's menu should have no saves, nor should it be loading a game, to begin with.
        self.assertFalse(self.mock_server.game_controller_ref.menu.saves)
        self.assertFalse(self.mock_server.game_controller_ref.menu.loading_game_multiplayer_status)

        # Process our test event, simulating a response from the global game server.
        self.request_handler.client_address = (GLOBAL_SERVER_HOST,)
        self.request_handler.process_query_saves_event(test_event, self.mock_socket)

        # The client's menu should now display the returned saves, as they are loading a multiplayer game.
        self.assertListEqual(test_event.saves, self.mock_server.game_controller_ref.menu.saves)
        # We also expect the loading game multiplayer status to be global, since the response was from the global game
        # server.
        self.assertEqual(MultiplayerStatus.GLOBAL,
                         self.mock_server.game_controller_ref.menu.loading_game_multiplayer_status)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

        # Now process our test event again, but this time simulate a response from a local game server.
        self.request_handler.client_address = ("127.0.0.1",)
        self.request_handler.process_query_saves_event(test_event, self.mock_socket)

        # The client's menu should again display the returned saves, as they are loading a multiplayer game.
        self.assertListEqual(test_event.saves, self.mock_server.game_controller_ref.menu.saves)
        # However, this time we expect the loading game multiplayer status to be local, since the response was from a
        # local game server.
        self.assertEqual(MultiplayerStatus.LOCAL,
                         self.mock_server.game_controller_ref.menu.loading_game_multiplayer_status)
        # Since this is a client, no packets should have been forwarded.
        self.mock_socket.sendto.assert_not_called()

    @patch("source.networking.event_listener.load_save_file")
    @patch("random.choice")
    def test_process_load_event_server(self, random_choice_mock: MagicMock, load_save_file_mock: MagicMock):
        """
        Ensure that the game server correctly processes load events.
        """
        test_event: LoadEvent = LoadEvent(EventType.LOAD, self.TEST_IDENTIFIER, "cool.save")
        self.mock_server.is_server = True
        taken_lobby_name: str = LOBBY_NAMES[0]
        test_lobby_name: str = LOBBY_NAMES[1]
        # Add in an extra game state so we can see the lobby name iteration process.
        self.mock_server.game_states_ref = {taken_lobby_name: GameState()}
        # We mock the method to initially return a lobby name that's already been taken, thus covering the case where
        # another lobby name needs to be randomly selected.
        random_choice_mock.side_effect = [taken_lobby_name, test_lobby_name]
        test_quads: List[List[Quad]] = [[Quad(Biome.DESERT, 1, 2, 3, 4, (5, 6))]]
        test_turn: int = 5
        expected_lobby: LobbyDetails = LobbyDetails(test_lobby_name, [
            PlayerDetails(self.TEST_GAME_STATE.players[0].name, self.TEST_GAME_STATE.players[0].faction, id=None),
            PlayerDetails(self.TEST_GAME_STATE.players[1].name, self.TEST_GAME_STATE.players[1].faction, id=None)
        ], self.TEST_GAME_CONFIG, test_turn)

        def mock_load(gs: GameState, _namer: Namer, _save: str) -> (GameConfig, List[List[Quad]]):
            """
            A mock function that does the bare minimum to avoid having to load in an actual save file. Assigns players
            and turn, and returns config and quads.
            :param gs: The game state to load data into.
            :param _namer: The game's Namer - unused in this function.
            :param _save: The save's name - unused in this function.
            :return: A test game config and test quads.
            """
            gs.players = self.TEST_GAME_STATE.players
            gs.turn = test_turn
            return self.TEST_GAME_CONFIG, test_quads

        # Rather than loading in an actual save file, we just use the mock function defined above.
        load_save_file_mock.side_effect = mock_load

        # Naturally, we expect this newly-loaded game to not exist in any capacity prior to loading it in.
        self.assertNotIn(test_lobby_name, self.mock_server.game_states_ref)
        self.assertNotIn(test_lobby_name, self.mock_server.namers_ref)
        self.assertNotIn(test_lobby_name, self.mock_server.game_clients_ref)
        self.assertNotIn(test_lobby_name, self.mock_server.move_makers_ref)
        self.assertNotIn(test_lobby_name, self.mock_server.lobbies_ref)

        # Process our test event.
        self.request_handler.process_load_event(test_event, self.mock_socket)

        # A game state should have been created for the loaded game.
        self.assertIn(test_lobby_name, self.mock_server.game_states_ref)
        new_game_state: GameState = self.mock_server.game_states_ref[test_lobby_name]
        # All loaded-in players should have an AI playstyle so that human players can take their place.
        self.assertTrue(all(p.ai_playstyle for p in new_game_state.players))
        # All references should be updated for the new game.
        self.assertIn(test_lobby_name, self.mock_server.namers_ref)
        self.assertFalse(self.mock_server.game_clients_ref[test_lobby_name])
        self.assertIn(test_lobby_name, self.mock_server.move_makers_ref)
        self.assertEqual(self.TEST_GAME_CONFIG, self.mock_server.lobbies_ref[test_lobby_name])
        # The loaded game should also be initialised.
        self.assertTrue(new_game_state.game_started)
        self.assertFalse(new_game_state.on_menu)
        self.assertIsNotNone(new_game_state.board)
        self.assertListEqual(test_quads, new_game_state.board.quads)
        self.assertEqual(new_game_state.board, self.mock_server.move_makers_ref[test_lobby_name].board_ref)
        # The lobby's details should also have been added on to the event, to be returned to the original dispatcher.
        self.assertEqual(expected_lobby, test_event.lobby)
        # Lastly, we expect the server to have sent a packet containing a JSON representation of the event to the client
        # that originally dispatched the create event.
        self.mock_socket.sendto.assert_called_with(json.dumps(test_event, cls=SaveEncoder).encode(),
                                                   (self.TEST_HOST, self.TEST_PORT))

    def test_process_load_event_client(self):
        """
        Ensure that game clients correctly process responses to load events.
        """
        test_lobby: LobbyDetails = LobbyDetails("Cool", [
            PlayerDetails(self.TEST_GAME_STATE.players[0].name, self.TEST_GAME_STATE.players[0].faction, id=None),
            PlayerDetails(self.TEST_GAME_STATE.players[1].name, self.TEST_GAME_STATE.players[1].faction, id=None)
        ], self.TEST_GAME_CONFIG, 5)
        expected_factions: List[Tuple[Faction, int]] = \
            [(Faction.AGRICULTURISTS, FACTION_COLOURS[Faction.AGRICULTURISTS]),
             (Faction.FRONTIERSMEN, FACTION_COLOURS[Faction.FRONTIERSMEN])]
        test_event: LoadEvent = LoadEvent(EventType.LOAD, self.TEST_IDENTIFIER, "cool.save", test_lobby)
        self.mock_server.is_server = False
        self.TEST_GAME_CONTROLLER.namer.reset = MagicMock()

        # Process our test event.
        self.request_handler.process_load_event(test_event, self.mock_socket)
        self.TEST_GAME_CONTROLLER.namer.reset.assert_called()
        # We expect the client to now have the appropriate lobby and available factions.
        self.assertListEqual([test_lobby], self.TEST_GAME_CONTROLLER.menu.multiplayer_lobbies)
        self.assertListEqual(expected_factions, self.TEST_GAME_CONTROLLER.menu.available_multiplayer_factions)
        # The client should also now be joining the game, rather than loading it.
        self.assertFalse(self.TEST_GAME_CONTROLLER.menu.loading_game)
        self.assertTrue(self.TEST_GAME_CONTROLLER.menu.joining_game)

    def test_process_keepalive_event_server(self):
        """
        Ensure that the game server correctly processes keepalive events.
        """
        test_event: Event = Event(EventType.KEEPALIVE, self.TEST_IDENTIFIER)
        self.mock_server.is_server = True
        # Pretend that there is one outstanding keepalive packet for this identifier.
        self.mock_server.keepalive_ctrs_ref[self.TEST_IDENTIFIER] = 1
        # Process our test event.
        self.request_handler.process_keepalive_event(test_event)
        # The keepalive counter for this identifier should now have been reset to zero.
        self.assertFalse(self.mock_server.keepalive_ctrs_ref[self.TEST_IDENTIFIER])

    @patch("source.networking.event_listener.get_identifier", return_value=TEST_IDENTIFIER)
    @patch.object(EventDispatcher, "dispatch_event")
    def test_process_keepalive_event_client(self, dispatch_mock: MagicMock, _: MagicMock):
        """
        Ensure that game clients correctly process, and respond to, keepalive events.
        """
        # Create a local game state for the client, with both the global event dispatcher and a local event dispatcher
        # as well.
        self.mock_server.game_states_ref["local"] = GameState()
        self.mock_server.game_states_ref["local"].event_dispatchers = {
            DispatcherKind.GLOBAL: EventDispatcher(),
            DispatcherKind.LOCAL: EventDispatcher("127.0.0.1")
        }
        # The identifier is None because it's the game server that is creating and sending this packet to the client.
        # This is different to other forwarding cases because those packets retain the original player identifier. For
        # example, if a player selected a new blessing, the event will have that player's identifier both when it gets
        # processed by the server and when it gets forwarded to the other players.
        test_event: Event = Event(EventType.KEEPALIVE, identifier=None)
        self.mock_server.is_server = False
        # Process our test event.
        self.request_handler.process_keepalive_event(test_event)
        # We expect the client to have dispatched a keepalive event back to both the global game server and its local
        # game server, with their identifier.
        dispatch_mock.assert_has_calls([call(Event(EventType.KEEPALIVE, self.TEST_IDENTIFIER)),
                                        call(Event(EventType.KEEPALIVE, self.TEST_IDENTIFIER))])

    @patch.object(Thread, "start")
    def test_event_listener_construction_server(self, thread_start_mock: MagicMock):
        """
        Ensure that the event listener is correctly constructed for the game server.
        """
        server_listener: EventListener = EventListener(is_server=True)

        # All state variables should be empty, with the exception of is_server which is naturally True, and the game
        # controller, which isn't required for the game server.
        self.assertFalse(server_listener.game_states)
        self.assertFalse(server_listener.namers)
        self.assertFalse(server_listener.move_makers)
        self.assertTrue(server_listener.is_server)
        self.assertIsNone(server_listener.game_controller)
        self.assertFalse(server_listener.game_clients)
        self.assertFalse(server_listener.lobbies)
        self.assertFalse(server_listener.clients)
        self.assertFalse(server_listener.keepalive_ctrs)

        # Since this is the game server, we also expect the keepalive thread to have been started.
        thread_start_mock.assert_called()

    @patch.object(Thread, "start")
    def test_event_listener_construction_client(self, thread_start_mock: MagicMock):
        """
        Ensure that event listeners are correctly constructed for clients.
        """
        test_game_states: Dict[str, GameState] = {"local": self.TEST_GAME_STATE}
        client_listener: EventListener = EventListener(is_server=False,
                                                       game_states=test_game_states,
                                                       game_controller=self.TEST_GAME_CONTROLLER)

        # Most state variables should be empty, but the game states and game controller provided in the constructor
        # should have been passed down. Naturally the client listener should also not be a server.
        self.assertEqual(test_game_states, client_listener.game_states)
        self.assertFalse(client_listener.namers)
        self.assertFalse(client_listener.move_makers)
        self.assertFalse(client_listener.is_server)
        self.assertEqual(self.TEST_GAME_CONTROLLER, client_listener.game_controller)
        self.assertFalse(client_listener.game_clients)
        self.assertFalse(client_listener.lobbies)
        self.assertFalse(client_listener.clients)
        self.assertFalse(client_listener.keepalive_ctrs)

        # Since this is a client, we don't expect it to start a new thread to manage keepalives.
        thread_start_mock.assert_not_called()

    @patch.object(Thread, "start", lambda *args: None)
    def test_event_listener_run_keepalive_scheduler(self):
        """
        Ensure that the keepalive scheduler is correctly run on the game server.
        """
        server_listener: EventListener = EventListener(is_server=True)
        scheduler: sched.scheduler = server_listener.keepalive_scheduler
        scheduler.enter = MagicMock()
        scheduler.run = MagicMock()

        server_listener.run_keepalive_scheduler()

        # Our mocked scheduler functions should have been called with the appropriate arguments.
        scheduler.enter.assert_called_with(5, 1, server_listener.run_keepalive, (scheduler,))
        scheduler.run.assert_called()

    @patch.object(Thread, "start", lambda *args: None)
    @patch("source.networking.event_listener.socket.socket")
    def test_event_listener_run_keepalive(self, socket_mock: MagicMock):
        """
        Ensure that the keepalive is correctly run on the game server.
        """
        server_listener: EventListener = EventListener(is_server=True)
        scheduler: sched.scheduler = server_listener.keepalive_scheduler
        scheduler.enter = MagicMock()
        socket_mock_instance: MagicMock = socket_mock.return_value
        # Simulate two clients.
        server_listener.clients = self.mock_server.clients_ref
        # One client hasn't responded to their last five keepalives, and one is a new client that has no counter.
        server_listener.keepalive_ctrs = {self.TEST_IDENTIFIER: 5}
        server_listener.game_clients = self.mock_server.game_clients_ref

        # Run the keepalive.
        server_listener.run_keepalive(scheduler)

        expected_keepalive_event_bytes: bytes = b'{"type": "KEEPALIVE", "identifier": null}'
        expected_leave_event_bytes: bytes = (b'{"type": "LEAVE", "identifier": 123, "lobby_name": "My favourite game", '
                                             b'"leaving_player_faction": null, "player_ai_playstyle": null}')
        expected_calls = [
            # We expect a keepalive event packet to have been sent to each client.
            call(expected_keepalive_event_bytes, (self.TEST_HOST, self.TEST_PORT)),
            call(expected_keepalive_event_bytes, (self.TEST_HOST_2, self.TEST_PORT_2)),
            # Subsequently, since the first client has thus not responded to their last six keepalives, we expect the
            # event listener to have sent a leave event to itself to remove the player who has lost connection.
            call(expected_leave_event_bytes, ("localhost", 9999))
        ]
        self.assertEqual(expected_calls, socket_mock_instance.sendto.mock_calls)
        # Both keepalive counters should have been incremented.
        self.assertDictEqual({self.TEST_IDENTIFIER: 6, self.TEST_IDENTIFIER_2: 1}, server_listener.keepalive_ctrs)
        # The client that lost connection should also have been removed.
        self.assertNotIn(self.TEST_IDENTIFIER, server_listener.clients)

    @patch.object(Thread, "start", lambda *args: None)
    @patch("source.networking.event_listener.UDPServer")
    def test_event_listener_run_server(self, udp_server_mock: MagicMock):
        """
        Ensure that the game server is correctly run, serving forever.
        """
        udp_server_mock_instance: MagicMock = udp_server_mock.return_value
        mock_entered_server: MagicMock = MagicMock()
        # Because the created UDPServer is used within a context manager, we need to mock what the with statement
        # returns. In this case, it is simply a mock object that will have attributes set and then called to serve
        # forever.
        udp_server_mock_instance.__enter__.return_value = mock_entered_server

        server_listener: EventListener = EventListener(is_server=True)
        server_listener.run()

        # We expect the UDP server itself to have been created with the correct port.
        udp_server_mock.assert_called_with(("0.0.0.0", 9999), RequestHandler)
        # The expected state variables for the game server should have been passed down as references to the UDP server.
        self.assertFalse(mock_entered_server.game_states_ref)
        self.assertFalse(mock_entered_server.namers_ref)
        self.assertFalse(mock_entered_server.move_makers_ref)
        self.assertTrue(mock_entered_server.is_server)
        self.assertIsNone(mock_entered_server.game_controller_ref)
        self.assertFalse(mock_entered_server.game_clients_ref)
        self.assertFalse(mock_entered_server.lobbies_ref)
        self.assertFalse(mock_entered_server.clients_ref)
        self.assertFalse(mock_entered_server.keepalive_ctrs_ref)
        # The UDP server should serve forever after it receives the state references.
        mock_entered_server.serve_forever.assert_called()

    @patch.object(Thread, "start", lambda *args: None)
    @patch.object(ThreadPoolExecutor, "submit", lambda *args: None)
    @patch("source.networking.event_listener.get_identifier", return_value=TEST_IDENTIFIER)
    @patch("socket.socket")
    @patch("source.networking.client.UPnP")
    @patch("source.networking.event_listener.UDPServer")
    def test_event_listener_run_client_with_upnp(self,
                                                 udp_server_mock: MagicMock,
                                                 upnp_mock: MagicMock,
                                                 socket_mock: MagicMock,
                                                 _: MagicMock):
        """
        Ensure that event listeners are correctly run for clients with UPnP available, serving forever.
        """
        # Set up a few test networking constants.
        test_port: int = 9999
        test_private_ip: str = "127.0.0.1"
        test_mapping_number: int = 1
        udp_server_mock_instance: MagicMock = udp_server_mock.return_value
        mock_entered_server: MagicMock = MagicMock()
        # Set the local listener's server address so that the UPnP mapping can be added correctly.
        mock_entered_server.server_address = test_private_ip, test_port
        # Because the created UDPServer is used within a context manager, we need to mock what the with statement
        # returns. In this case, it is simply a mock object that will have attributes set and then called to serve
        # forever.
        udp_server_mock_instance.__enter__.return_value = mock_entered_server
        upnp_mock_instance: MagicMock = upnp_mock.return_value
        # Mock out the existing UPnP port mappings to have just one. Note that the date used will always be prior to the
        # current date.
        upnp_mock_instance.getgenericportmapping = \
            MagicMock(side_effect=[(test_mapping_number, "UDP", (test_private_ip, 1),
                                    "Microcosm 1970-01-01", "1", "", test_port), None])
        socket_mock_instance: MagicMock = socket_mock.return_value
        # Mock out the call to retrieve the client's private IP.
        socket_mock_instance.getsockname = MagicMock(return_value=(test_private_ip,))
        # Pass through the test game state and controller, as we do for client listeners.
        test_game_states: Dict[str, GameState] = {"local": self.TEST_GAME_STATE}
        client_listener: EventListener = EventListener(is_server=False,
                                                       game_states=test_game_states,
                                                       game_controller=self.TEST_GAME_CONTROLLER)

        # Before the listener is run, the menu should still say that it's 'Connecting to server...'.
        self.assertIsNone(self.TEST_GAME_CONTROLLER.menu.upnp_enabled)

        # Run the event listener.
        client_listener.run()

        # We expect the UDP server itself to have been created with the correct port.
        udp_server_mock.assert_called_with(("0.0.0.0", 0), RequestHandler)
        # We expect the correct UPnP setup to have occurred, discovering and selecting from the available UPnP devices
        # on the network.
        upnp_mock_instance.discover.assert_called()
        upnp_mock_instance.selectigd.assert_called()
        # Because our mocked-out UPnP port mapping was from 1970, and because it was for the local machine, we expect it
        # to have been deleted.
        upnp_mock_instance.deleteportmapping.assert_called_with(test_mapping_number, "UDP")
        # We then expect a new mapping to have been added with the appropriate networking details and date.
        upnp_mock_instance.addportmapping.assert_called_with(test_port, "UDP", test_private_ip,
                                                             test_port, f"Microcosm {datetime.date.today()}", "")
        # With the UPnP setup done, the client should then send off a packet to the game server alerting it that the
        # client will be sending more requests.
        socket_mock_instance.sendto.assert_called_with(b'{"type":"REGISTER","identifier":123,"port":9999}',
                                                       (GLOBAL_SERVER_HOST, SERVER_PORT))
        # The main menu should also now be shown.
        self.assertTrue(self.TEST_GAME_CONTROLLER.menu.upnp_enabled)
        # The expected state variables for the client listener should have been passed down as references to the UDP
        # server.
        self.assertEqual(test_game_states, mock_entered_server.game_states_ref)
        self.assertFalse(mock_entered_server.namers_ref)
        self.assertFalse(mock_entered_server.move_makers_ref)
        self.assertFalse(mock_entered_server.is_server)
        self.assertEqual(self.TEST_GAME_CONTROLLER, mock_entered_server.game_controller_ref)
        self.assertFalse(mock_entered_server.game_clients_ref)
        self.assertFalse(mock_entered_server.lobbies_ref)
        self.assertFalse(mock_entered_server.clients_ref)
        self.assertFalse(mock_entered_server.keepalive_ctrs_ref)
        # Lastly, the UDP server should serve forever after it receives the state references.
        mock_entered_server.serve_forever.assert_called()

    @patch.object(Thread, "start", lambda *args: None)
    @patch.object(ThreadPoolExecutor, "submit", lambda *args: None)
    @patch("socket.socket")
    @patch("source.networking.client.UPnP")
    @patch("source.networking.event_listener.UDPServer")
    def test_event_listener_run_client_without_upnp(self,
                                                    udp_server_mock: MagicMock,
                                                    upnp_mock: MagicMock,
                                                    socket_mock: MagicMock):
        """
        Ensure that event listeners are correctly run for clients with UPnP unavailable, not serving at all.
        """
        udp_server_mock_instance: MagicMock = udp_server_mock.return_value
        mock_entered_server: MagicMock = MagicMock()
        # Because the created UDPServer is used within a context manager, we need to mock what the with statement
        # returns. In this case, it is simply a mock object that will be unmodified since UPnP is unavailable.
        udp_server_mock_instance.__enter__.return_value = mock_entered_server
        upnp_mock_instance: MagicMock = upnp_mock.return_value
        # When there are no available UPnP devices on the client's network, then the selectigd() function will raise an
        # Exception - we mock that here.
        upnp_mock_instance.selectigd.side_effect = Exception()
        socket_mock_instance: MagicMock = socket_mock.return_value
        # We also need to mock out the private IP returned by the socket for when the client broadcasts to other hosts
        # on its local network.
        socket_mock_instance.getsockname.return_value = ["127.0.0.1"]
        # Pass through the test game state and controller, as we do for client listeners.
        test_game_states: Dict[str, GameState] = {"local": self.TEST_GAME_STATE}
        client_listener: EventListener = EventListener(is_server=False,
                                                       game_states=test_game_states,
                                                       game_controller=self.TEST_GAME_CONTROLLER)

        # Before the listener is run, the menu should still say that it's 'Connecting to server...'.
        self.assertIsNone(self.TEST_GAME_CONTROLLER.menu.upnp_enabled)

        # Run the event listener.
        client_listener.run()

        # We expect the UDP server itself to have been created with the correct port.
        udp_server_mock.assert_called_with(("0.0.0.0", 0), RequestHandler)
        # We expect UPnP setup to have been attempted, however in our simulation, no devices were discovered and so an
        # Exception was raised.
        upnp_mock_instance.discover.assert_called()
        upnp_mock_instance.selectigd.assert_called()
        # Because UPnP initialisation failed, we expect no mappings to be deleted nor added.
        upnp_mock_instance.deleteportmapping.assert_not_called()
        upnp_mock_instance.addportmapping.assert_not_called()
        # Similarly, the client should not have sent a packet to the game server since it will not be able to receive
        # any.
        socket_mock_instance.sendto.assert_not_called()
        # Thus, we expect the menu to now be displayed, but with multiplayer features disabled.
        self.assertFalse(self.TEST_GAME_CONTROLLER.menu.upnp_enabled)


if __name__ == '__main__':
    unittest.main()
