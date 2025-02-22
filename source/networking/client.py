import datetime
import json
import os
import socket
import uuid
from enum import Enum
from ipaddress import IPv4Network
from socketserver import UDPServer

from miniupnpc import UPnP

from source.networking.events import Event, RegisterEvent, EventType
from source.saving.save_encoder import SaveEncoder


# The IP address of the game server, and the port it is reachable on.
HOST, PORT = "170.64.142.122", 9999


def dispatch_event(evt: Event):
    """
    Send a UDP packet with the JSON-encoded bytes of the supplied event to the game server.
    :param evt: The event to send to the game server for processing.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # We use SaveEncoder here too for the same custom JSON output as with game saves.
    evt_json: str = json.dumps(evt, separators=(",", ":"), cls=SaveEncoder)
    sock.sendto(evt_json.encode(), (HOST, PORT))


class DispatcherKind(Enum):
    LOCAL = "LOCAL"
    GLOBAL = "GLOBAL"


class EventDispatcher:
    def __init__(self, host: str = HOST):
        self.host: str = host

    def dispatch_event(self, evt: Event):
        """
        Send a UDP packet with the JSON-encoded bytes of the supplied event to the game server.
        :param evt: The event to send to the game server for processing.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # We use SaveEncoder here too for the same custom JSON output as with game saves.
        evt_json: str = json.dumps(evt, separators=(",", ":"), cls=SaveEncoder)
        sock.sendto(evt_json.encode(), (self.host, PORT))


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


def initialise_upnp(private_ip: str, server: UDPServer):
    # Initialise UPnP, discovering and then selecting a valid UPnP IGD device on the connected network,
    # where IGD refers to the protocol used for UPnP.
    upnp = UPnP()
    upnp.discover()
    upnp.selectigd()
    mapping_idx: int = 0
    todays_date: datetime.date = datetime.date.today()
    # For security reasons, we don't really want to leave these UPnP ports open permanently (even though
    # nothing is listening). As such, we check all existing port mappings on the network, and delete any
    # mappings that were created on previous days. Additionally, if a previous mapping was for this
    # machine, we delete the old one and make a new one.
    while (port_mapping := upnp.getgenericportmapping(mapping_idx)) is not None:
        mapping_name: str = port_mapping[3]
        if mapping_name.startswith("Microcosm"):
            # Because ISO dates can be sorted alphabetically to sort them chronologically, we can just
            # extract the date from the mapping and compare the strings.
            mapping_is_old: bool = mapping_name[10:] < str(todays_date)
            mapping_is_for_this_machine: bool = port_mapping[2][0] == private_ip
            if mapping_is_old or mapping_is_for_this_machine:
                upnp.deleteportmapping(port_mapping[0], "UDP")
        mapping_idx += 1
    # Now create a new port mapping for this machine's private IP and dynamic listener port, complete
    # with the creation date, so it can be deleted later.
    upnp.addportmapping(server.server_address[1], "UDP", private_ip, server.server_address[1],
                        f"Microcosm {todays_date}", "")


def broadcast_to_local_network_hosts(private_ip: str, client_port: int):
    local_network: IPv4Network = IPv4Network(f"{private_ip}/24", strict=False)
    for host in local_network.hosts():
        # TODO this is very slow - speed it up
        print(host)
        dispatcher: EventDispatcher = EventDispatcher(str(host))
        dispatcher.dispatch_event(RegisterEvent(EventType.REGISTER, get_identifier(), client_port))
