import json
import socket
import unittest
from unittest.mock import MagicMock, call, patch

from source.foundation.catalogue import LOBBY_NAMES, PLAYER_NAMES, FACTION_COLOURS, BLESSINGS, PROJECTS, IMPROVEMENTS, \
    UNIT_PLANS
from source.foundation.models import PlayerDetails, Faction, GameConfig, Player, Settlement, ResourceCollection, \
    OngoingBlessing, Construction, InvestigationResult
from source.game_management.game_controller import GameController
from source.game_management.game_state import GameState
from source.networking.event_listener import RequestHandler, MicrocosmServer
from source.networking.events import EventType, RegisterEvent, Event, CreateEvent, InitEvent, UpdateEvent, \
    UpdateAction, QueryEvent, LeaveEvent, JoinEvent, EndTurnEvent, UnreadyEvent, AutofillEvent, SaveEvent, \
    QuerySavesEvent, LoadEvent, FoundSettlementEvent, SetBlessingEvent, SetConstructionEvent, MoveUnitEvent, \
    DeployUnitEvent, GarrisonUnitEvent, InvestigateEvent, BesiegeSettlementEvent, BuyoutConstructionEvent, \
    DisbandUnitEvent, AttackUnitEvent, AttackSettlementEvent, HealUnitEvent, BoardDeployerEvent, DeployerDeployEvent
from source.saving.save_encoder import SaveEncoder


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
    TEST_EVENT: RegisterEvent = RegisterEvent(EventType.REGISTER, TEST_IDENTIFIER, TEST_PORT)
    TEST_EVENT_BYTES: bytes = b'{"type":"REGISTER","identifier":123,"port":9999}'
    TEST_GAME_NAME: str = "My favourite game"
    TEST_GAME_CONFIG: GameConfig = GameConfig(2, Faction.AGRICULTURISTS, True, True, True, True)

    @patch("source.game_management.game_controller.MusicPlayer")
    def setUp(self, _: MagicMock):
        """
        Set up some test models, our mock server, and request handler - noting that the call of the handler's
        constructor actually handles the test event given in the request. Note that we mock out MusicPlayer so that the
        construction of the GameController doesn't try to play the menu music.
        """
        self.TEST_SETTLEMENT: Settlement = Settlement("Testville", (0, 0), [], [], ResourceCollection(), [])
        self.TEST_GAME_STATE: GameState = GameState()
        self.TEST_GAME_STATE.players = [
            Player("Uno", Faction.AGRICULTURISTS, 0, settlements=[self.TEST_SETTLEMENT]),
            Player("Dos", Faction.FRONTIERSMEN, 1)
        ]

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
        self.mock_server.lobbies_ref = {}
        self.mock_server.game_states_ref = {}
        self.mock_server.game_controller_ref = GameController()
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
        event_processed: RegisterEvent = self.request_handler.process_event.call_args[0][0]
        socket_processed: socket.socket = self.request_handler.process_event.call_args[0][1]
        self.assertEqual(self.TEST_EVENT.type, event_processed.type)
        self.assertEqual(self.TEST_EVENT.identifier, event_processed.identifier)
        self.assertEqual(self.TEST_EVENT.port, event_processed.port)
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

    def test_forward_packet(self):
        """
        Ensure that packets are correctly forwarded to the correct clients under the correct conditions.
        """
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
            self.request_handler.__setattr__(expected_method, MagicMock())
            self.request_handler.process_event(event, self.mock_socket)
            expected_args: list = [event, self.mock_socket] if with_sock else [event]
            # Ensure the method was called with the expected arguments.
            self.request_handler.__getattribute__(expected_method).assert_called_with(*expected_args)

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
                            "process_register_event", with_sock=False)
        validate_event_type(EndTurnEvent(EventType.END_TURN, self.TEST_IDENTIFIER, self.TEST_GAME_NAME),
                            "process_end_turn_event")
        validate_event_type(UnreadyEvent(EventType.UNREADY, self.TEST_IDENTIFIER,
                                         self.TEST_GAME_NAME, Faction.AGRICULTURISTS),
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
            self.request_handler.__setattr__(expected_method, MagicMock())
            self.request_handler.process_update_event(event, self.mock_socket)
            # Ensure the method was called with the expected arguments.
            self.request_handler.__getattribute__(expected_method).assert_called_with(event, self.mock_socket)

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

    def test_process_set_blessing_event_server(self):
        """
        Ensure that the game server correctly processes set blessing events.
        """
        test_event: SetBlessingEvent = SetBlessingEvent(EventType.UPDATE, self.TEST_IDENTIFIER,
                                                        UpdateAction.SET_BLESSING, self.TEST_GAME_NAME,
                                                        Faction.AGRICULTURISTS, OngoingBlessing(BLESSINGS["beg_spl"]))
        self.mock_server.is_server = True
        self.mock_server.game_states_ref[self.TEST_GAME_NAME] = self.TEST_GAME_STATE
        self.mock_socket.sendto = MagicMock()

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
        self.mock_socket.sendto = MagicMock()

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
        self.mock_socket.sendto = MagicMock()

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
        self.mock_socket.sendto = MagicMock()

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


if __name__ == '__main__':
    unittest.main()
