from __future__ import annotations

import binascii
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from deebot_client.events import Position, PositionsEvent, RoomsEvent
from deebot_client.events.map import (
    CachedMapInfoEvent,
    MajorMapEvent,
    Map,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MapTraceEvent,
    MinorMapEvent,
)
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import Room
from deebot_client.ngiot_client import APN_MAP_DETAILS
from deebot_client.rs.map import PositionType, RotationAngle

from .common import NgiotJsonGetCommand