from __future__ import annotations

import json
import socket
import typing

from source.saving.save_encoder import SaveEncoder

if typing.TYPE_CHECKING:
    from source.networking.event_listener import Event

HOST, PORT = "localhost", 9999


def dispatch_event(evt: Event):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    evt_json: str = json.dumps(evt, cls=SaveEncoder)
    sock.sendto(evt_json.encode(), (HOST, PORT))


"""
Things to be updated by client (i.e. that other players need to care about)
- Updating construction
- Updating blessing
- Removing unit

"""

# Will need to poll for changes since last
# Server will need to keep track of all game events, but only needs the initial game state
