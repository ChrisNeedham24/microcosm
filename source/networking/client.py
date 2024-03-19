from __future__ import annotations

import json
import os
import socket
import uuid

from source.networking.events import Event
from source.saving.save_encoder import SaveEncoder


HOST, PORT = "170.64.142.122", 9999


def dispatch_event(evt: Event):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    evt_json: str = json.dumps(evt, cls=SaveEncoder)
    sock.sendto(evt_json.encode(), (HOST, PORT))


def get_identifier() -> int:
    return hash((uuid.getnode(), os.getpid()))


"""
Things to be updated by client (i.e. that other players need to care about)
- Updating construction
- Updating blessing
- Removing unit

"""

# Will need to poll for changes since last
# Server will need to keep track of all game events, but only needs the initial game state
