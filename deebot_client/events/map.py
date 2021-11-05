"""Map event module."""
from dataclasses import dataclass
from enum import Enum
from typing import List

from ..events import EventDto


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
class PositionsEventDto(EventDto):
    """Position event representation."""

    positions: List[Position]


@dataclass(frozen=True)
class MapTraceEventDto(EventDto):
    """Map trace event representation."""

    start: int
    total: int
    data: str


@dataclass(frozen=True)
class MajorMapEventDto(EventDto):
    """Major map event."""

    requested: bool
    map_id: str
    values: List[str]
