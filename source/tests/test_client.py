import unittest
from unittest.mock import patch, MagicMock

from source.networking.client import dispatch_event, HOST, PORT, get_identifier
from source.networking.events import Event, EventType


class ClientTest(unittest.TestCase):
    """
    The test class for client.py.
    """

    @patch("source.networking.client.socket.socket")
    def test_dispatch_event(self, socket_mock: MagicMock):
        """
        Ensure that events are serialised and dispatched correctly.
        """
        socket_mock_instance: MagicMock = socket_mock.return_value
        test_event: Event = Event(EventType.REGISTER, 123)
        dispatch_event(test_event)
        socket_mock_instance.sendto.assert_called_with(b'{"type": "REGISTER", "identifier": 123}', (HOST, PORT))

    @patch("uuid.getnode")
    @patch("os.getpid")
    def test_get_identifier(self, pid_mock: MagicMock, node_mock: MagicMock):
        """
        Ensure that a machine's identifier is correctly determined.
        """
        pid_mock.return_value = 2
        node_mock.return_value = 1
        # That's the hash of (1, 2).
        self.assertEqual(-3550055125485641917, get_identifier())


if __name__ == '__main__':
    unittest.main()
