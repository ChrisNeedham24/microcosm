import socket
import unittest
from unittest.mock import MagicMock, call

from source.foundation.models import PlayerDetails, Faction
from source.networking.event_listener import RequestHandler, MicrocosmServer
from source.networking.events import EventType, RegisterEvent


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

    def setUp(self):
        """
        Set up our mock server and request handler - noting that the call of the handler's constructor actually handles
        the test event given in the request.
        """
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


if __name__ == '__main__':
    unittest.main()
