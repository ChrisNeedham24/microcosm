import datetime
import importlib
import sys
import unittest
from ipaddress import IPv4Network
from typing import Dict
from unittest.mock import patch, MagicMock, call

from source.foundation.models import MultiplayerStatus
from source.networking import client
from source.networking.client import dispatch_event, GLOBAL_SERVER_HOST, SERVER_PORT, get_identifier, DispatcherKind, \
    EventDispatcher, initialise_upnp, broadcast_to_local_network_hosts
from source.networking.events import Event, EventType, RegisterEvent


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
    def test_event_dispatcher_dispatch_event(self, socket_mock: MagicMock):
        """
        Ensure that events are serialised and dispatched correctly in an EventDispatcher.
        """
        socket_mock_instance: MagicMock = socket_mock.return_value
        test_event: Event = Event(EventType.REGISTER, 123)
        test_host: str = "127.0.0.1"

        dispatcher: EventDispatcher = EventDispatcher(test_host)
        dispatcher.dispatch_event(test_event)
        socket_mock_instance.sendto.assert_called_with(b'{"type":"REGISTER","identifier":123}',
                                                       (test_host, SERVER_PORT))

    @patch("source.networking.client.socket.socket")
    def test_dispatch_event(self, socket_mock: MagicMock):
        """
        Ensure that events are serialised and dispatched correctly, based on the given dispatchers and multiplayer
        status.
        """
        socket_mock_instance: MagicMock = socket_mock.return_value
        test_event: Event = Event(EventType.REGISTER, 123)
        test_local_host: str = "127.0.0.1"
        test_dispatchers: Dict[DispatcherKind, EventDispatcher] = {
            DispatcherKind.GLOBAL: EventDispatcher(),
            DispatcherKind.LOCAL: EventDispatcher(test_local_host)
        }

        # For the first part of this test, we dispatch an event in a global multiplayer game.
        dispatch_event(test_event, test_dispatchers, MultiplayerStatus.GLOBAL)
        # The serialised event should have been sent to the global game server.
        socket_mock_instance.sendto.assert_called_with(b'{"type":"REGISTER","identifier":123}',
                                                       (GLOBAL_SERVER_HOST, SERVER_PORT))

        socket_mock_instance.reset_mock()

        # For the second part of this test, we dispatch an event in a local multiplayer game.
        dispatch_event(test_event, test_dispatchers, MultiplayerStatus.LOCAL)
        # The serialised event should have been sent to the local game server with the custom host.
        socket_mock_instance.sendto.assert_called_with(b'{"type":"REGISTER","identifier":123}',
                                                       (test_local_host, SERVER_PORT))

        socket_mock_instance.reset_mock()

        # Lastly, we simulate a case where the multiplayer status is somehow disabled and an event has been dispatched.
        # For what it's worth, this should never happen.
        dispatch_event(test_event, test_dispatchers, MultiplayerStatus.DISABLED)
        # Naturally, no event should have been dispatched.
        socket_mock_instance.sendto.assert_not_called()

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

    @patch("source.networking.client.UPnP")
    def test_initialise_upnp(self, upnp_mock: MagicMock):
        """
        Ensure that UPnP can be successfully initialised, adding and removing port mappings as necessary.
        """
        # Set up a few test networking constants.
        test_port: int = 9999
        test_private_ip: str = "127.0.0.1"
        test_mapping_number: int = 1
        upnp_mock_instance: MagicMock = upnp_mock.return_value
        # Mock out the existing UPnP port mappings to have just one. Note that the date used will always be prior to the
        # current date.
        upnp_mock_instance.getgenericportmapping = \
            MagicMock(side_effect=[(test_mapping_number, "UDP", (test_private_ip, 1),
                                    "Microcosm 1970-01-01", "1", "", test_port), None])

        initialise_upnp(test_private_ip, test_port)

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

    @patch("source.networking.client.get_identifier")
    @patch("source.networking.client.EventDispatcher")
    def test_broadcast_to_local_network_hosts(self, dispatcher_mock: MagicMock, identifier_mock: MagicMock):
        """
        Ensure that any hosts on the local network are pinged to see if they are hosting a local game server.
        """
        test_identifier: int = 1234
        test_port: int = 11111
        identifier_mock.return_value = test_identifier

        broadcast_to_local_network_hosts("127.0.0.1", test_port)

        # We expect each theoretical host to have been pinged with a register event containing the correct identifier
        # and port.
        for octet in range(1, 255):
            self.assertTrue(call(f"127.0.0.{octet}") in dispatcher_mock.mock_calls)
            self.assertTrue(call().dispatch_event(RegisterEvent(EventType.REGISTER, test_identifier, test_port))
                            in dispatcher_mock.mock_calls)


if __name__ == '__main__':
    unittest.main()
