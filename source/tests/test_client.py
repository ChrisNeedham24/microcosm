import importlib
import sys
import unittest
from unittest.mock import patch, MagicMock

from source.foundation.models import MultiplayerStatus
from source.networking import client
from source.networking.client import dispatch_event, GLOBAL_SERVER_HOST, SERVER_PORT, get_identifier, DispatcherKind, \
    EventDispatcher
from source.networking.events import Event, EventType


class ClientTest(unittest.TestCase):
    """
    The test class for client.py.
    """

    @patch("site.getusersitepackages")
    @patch("ctypes.cdll.LoadLibrary")
    @patch("ctypes.CDLL")
    @patch("platform.system", return_value="Windows")
    def test_windows_dll_verification(self,
                                      _: MagicMock,
                                      cdll_construction_mock: MagicMock,
                                      cdll_load_mock: MagicMock,
                                      user_site_packages_mock: MagicMock):
        """
        Ensure that the miniupnpc DLL is correctly manually loaded or not manually loaded, depending on whether it has
        already been automatically loaded.
        """
        # First we need to reload the import since naturally client.py has already been imported in this test suite.
        importlib.reload(client)
        # In the EXE case, we expect the DLL to already be loaded, so no manual load should occur.
        cdll_construction_mock.assert_called_with("miniupnpc.dll")
        cdll_load_mock.assert_not_called()
        # We simulate the playing from source/package cases by raising an error when constructing the DLL object, since
        # it's not present in those cases.
        cdll_construction_mock.side_effect = FileNotFoundError()
        # Simulate the source case.
        importlib.reload(client)
        # In this case, we expect an attempt to be made to construct the DLL object, but ultimately for the DLL to be
        # manually loaded from source.
        cdll_construction_mock.assert_called_with("miniupnpc.dll")
        cdll_load_mock.assert_called_with("source/resources/dll/miniupnpc.dll")
        # Simulate the package case by mocking out the user site-packages path and sys.modules.
        user_site_packages_path: str = "/tmp/site-packages"
        user_site_packages_mock.return_value = user_site_packages_path
        # This mock is definitely not normal, but it does serve our purpose by defining the key against a real module.
        sys.modules["microcosm"] = client
        importlib.reload(client)
        # In this case, we also expect an attempt to be made to construct the DLL object, but this time we expect the
        # DLL to be manually loaded from user site-packages.
        cdll_construction_mock.assert_called_with("miniupnpc.dll")
        cdll_load_mock.assert_called_with(f"{user_site_packages_path}/microcosm/source/resources/dll/miniupnpc.dll")

    @patch("source.networking.client.socket.socket")
    def test_dispatch_event(self, socket_mock: MagicMock):
        """
        Ensure that events are serialised and dispatched correctly.
        """
        socket_mock_instance: MagicMock = socket_mock.return_value
        test_event: Event = Event(EventType.REGISTER, 123)
        dispatch_event(test_event, {DispatcherKind.GLOBAL: EventDispatcher()}, MultiplayerStatus.GLOBAL)
        socket_mock_instance.sendto.assert_called_with(b'{"type":"REGISTER","identifier":123}',
                                                       (GLOBAL_SERVER_HOST, SERVER_PORT))

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
