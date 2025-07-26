import datetime
import json
import os
import platform
import socket
import uuid
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from ipaddress import IPv4Address, IPv4Network
from site import getusersitepackages
from typing import Dict

# For Windows clients we need to ensure that the miniupnpc DLL is loaded before attempting to import the module.
if platform.system() == "Windows":
    from ctypes import cdll, CDLL
    import sys
    # Clients playing via the bundled EXE should already have the DLL loaded, since it's bundled into the EXE itself.
    try:
        CDLL("miniupnpc.dll")
    # However, clients playing via a pip install or from source will need to load the DLL manually.
    except FileNotFoundError:
        if "microcosm" in sys.modules:
            cdll.LoadLibrary(f"{getusersitepackages()}/microcosm/source/resources/dll/miniupnpc.dll")
        else:
            cdll.LoadLibrary("source/resources/dll/miniupnpc.dll")
# We need to disable a lint rule for the miniupnpc import because it doesn't actually declare UPnP in its module. This
# isn't our fault, so we can just disable the rule.
# pylint: disable=no-name-in-module
from miniupnpc import UPnP

from source.foundation.models import MultiplayerStatus
from source.networking.events import Event, RegisterEvent, EventType
from source.saving.save_encoder import SaveEncoder


# The IP address of the global game server.
GLOBAL_SERVER_HOST: str = "170.64.142.122"
# The port at which all game servers are reachable, both global and local.
SERVER_PORT: int = 9999


class DispatcherKind(Enum):
    """
    The two different kinds of EventDispatchers; an EventDispatcher can be for either a local game server or for the
    global game server.
    """
    LOCAL = "LOCAL"
    GLOBAL = "GLOBAL"


class EventDispatcher:
    """
    Dispatches multiplayer game events to its supplied host.
    """

    def __init__(self, host: str = GLOBAL_SERVER_HOST):
        """
        Creates the dispatcher, setting the game server host IP.
        :param host: The IP address of the game server for this dispatcher.
        """
        self.host: str = host

    def dispatch_event(self, evt: Event):
        """
        Send a UDP packet with the JSON-encoded bytes of the supplied event to the game server.
        :param evt: The event to send to the game server for processing.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # We use SaveEncoder here too for the same custom JSON output as with game saves.
        evt_json: str = json.dumps(evt, separators=(",", ":"), cls=SaveEncoder)
        sock.sendto(evt_json.encode(), (self.host, SERVER_PORT))


def dispatch_event(evt: Event,
                   dispatchers: Dict[DispatcherKind, EventDispatcher],
                   multiplayer_status: MultiplayerStatus):
    """
    Send a UDP packet with the JSON-encoded bytes of the supplied event to the appropriate game server, using its
    associated dispatcher, which is based on the given multiplayer status.
    :param evt: The event to send to the game server for processing.
    :param dispatchers: The available dispatchers for the current running instance.
    :param multiplayer_status: The multiplayer status for the current game. This will either be LOCAL or GLOBAL; if this
                               is DISABLED, then something has gone horribly wrong.
    """
    match multiplayer_status:
        case MultiplayerStatus.GLOBAL:
            dispatchers[DispatcherKind.GLOBAL].dispatch_event(evt)
        case MultiplayerStatus.LOCAL:
            dispatchers[DispatcherKind.LOCAL].dispatch_event(evt)
        # As mentioned above, while it would be extremely odd for an event to be dispatched in a single-player game,
        # it's probably not one worth crashing the game over, so we just ignore them.
        case _:
            pass


def get_identifier() -> int:
    """
    Get the identifier for the current running instance of Microcosm.
    :return: The process-level identifier for the current running instance.
    """
    # uuid.getnode() returns a hardware address unique to this machine. Naturally, os.getpid() returns the PID. Combined
    # as a hash, they serve as a unique identifier for the running instance. Technically this means that the multiple
    # players could play on the same machine, but as it currently stands this is impossible due to UPnP limitations. In
    # future this may prove useful for LAN games, however.
    return hash((uuid.getnode(), os.getpid()))


def initialise_upnp(private_ip: str, port: int):
    """
    Initialise UPnP on the client machine, removing any old port mappings and adding a new one for the current game
    session.
    :param private_ip: The client's private IP on its local network. Used to add the port mapping, forwarding traffic
                       from external sources to this client.
    :param port: The dynamic listener port on the client to forward external traffic to via UPnP.
    """
    # Initialise UPnP, discovering and then selecting a valid UPnP IGD device on the connected network, where IGD refers
    # to the protocol used for UPnP.
    upnp = UPnP()
    upnp.discover()
    upnp.selectigd()
    mapping_idx: int = 0
    todays_date: datetime.date = datetime.date.today()
    # For security reasons, we don't really want to leave these UPnP ports open permanently (even though nothing is
    # listening). As such, we check all existing port mappings on the network, and delete any mappings that were created
    # on previous days. Additionally, if a previous mapping was for this machine, we delete the old one and make a new
    # one.
    while (port_mapping := upnp.getgenericportmapping(mapping_idx)) is not None:
        mapping_name: str = port_mapping[3]
        if mapping_name.startswith("Microcosm"):
            # Because ISO dates can be sorted alphabetically to sort them chronologically, we can just extract the date
            # from the mapping and compare the strings.
            mapping_is_old: bool = mapping_name[10:] < str(todays_date)
            mapping_is_for_this_machine: bool = port_mapping[2][0] == private_ip
            if mapping_is_old or mapping_is_for_this_machine:
                upnp.deleteportmapping(port_mapping[0], "UDP")
        mapping_idx += 1
    # Now create a new port mapping for this machine's private IP and dynamic listener port, complete with the creation
    # date, so it can be deleted later.
    upnp.addportmapping(port, "UDP", private_ip, port, f"Microcosm {todays_date}", "")


def broadcast_to_local_network_hosts(private_ip: str, client_port: int):
    """
    Broadcast to all other IP addresses on the given private IP's local network, alerting any potential local game
    servers of a new client.
    :param private_ip: The client's private IP on its local network. Used to determine the IP addresses for all other
                       hosts on the network.
    :param client_port: The dynamic listener port on the client. Used for the client registration process with a game
                        server.
    """
    # We need strict to be False here so that we can use the /24 subnet mask.
    local_network: IPv4Network = IPv4Network(f"{private_ip}/24", strict=False)

    def ping_host(host: IPv4Address):
        """
        Ping the supplied host with a register event for the client.
        :param host: The IP address for the host to ping.
        """
        dispatcher: EventDispatcher = EventDispatcher(str(host))
        dispatcher.dispatch_event(RegisterEvent(EventType.REGISTER, get_identifier(), client_port))

    # Ping all the hosts in parallel so it doesn't take too long.
    with ThreadPoolExecutor(max_workers=10) as executor:
        for h in local_network.hosts():
            executor.submit(ping_host, h)
