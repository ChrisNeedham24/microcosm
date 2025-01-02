import json
import os
import socket
import uuid

from source.networking.events import Event
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
