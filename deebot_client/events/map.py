"""Map event module."""
from dataclasses import dataclass
from enum import Enum
from typing import List

from ..events import Event


class PositionType(str, Enum):
    """Position type enum."""

    DEEBOT = "deebotPos"
    CHARGER = "chargePos"


@dataclass(frozen=True)
class Position:
    """Position representation."""

    type: PositionType
    x: int
    y: int


@dataclass(frozen=True)
class PositionsEvent(Event):
    """Position event representation."""

    positions: List[Position]


@dataclass(frozen=True)
class MapTraceEvent(Event):
    """Map trace event representation."""

    start: int
    total: int
    data: str


@dataclass(frozen=True)
class MajorMapEvent(Event):
    """Major map event."""

    requested: bool
    map_id: str
    values: List[str]


@dataclass(frozen=True)
class MapSetEvent(Event):
    """Map set event."""

    rooms_count: int


@dataclass(frozen=True)
class MinorMapEvent(Event):
    """Minor map event."""

    index: int
    value: str
