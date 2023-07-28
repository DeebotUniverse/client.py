"""Map event module."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique
from typing import Any

from ..events import Event


@unique
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

    positions: list[Position]


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
    values: list[str]


@dataclass(frozen=True)
class MinorMapEvent(Event):
    """Minor map event."""

    index: int
    value: str


@unique
class MapSetType(str, Enum):
    """Map set type enum."""

    ROOMS = "ar"
    VIRTUAL_WALLS = "vw"
    NO_MOP_ZONES = "mw"

    @classmethod
    def has_value(cls, value: Any) -> bool:
        """Check if value exists."""

        return value in cls._value2member_map_


@dataclass(frozen=True)
class MapSetEvent(Event):
    """Map set event."""

    type: MapSetType
    subsets: list[int]


@dataclass(frozen=True)
class MapSubsetEvent(Event):
    """Map subset event."""

    id: int
    type: MapSetType
    coordinates: str
    name: str | None = None


@dataclass(frozen=True)
class CachedMapInfoEvent(Event):
    """Cached map info event."""

    name: str
    active: bool


@dataclass(frozen=True)
class MapChangedEvent(Event):
    """Map changed event."""

    when: datetime
