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
