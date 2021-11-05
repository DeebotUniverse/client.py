"""Events module."""

from dataclasses import dataclass
from enum import Enum, unique
from typing import Any, Dict, List, Optional

from ..events.base import EventDto
from ..models import Room, VacuumState
from ..util import DisplayNameIntEnum
from .map import (
    MajorMapEventDto,
    MapSetEventDto,
    MapTraceEventDto,
    Position,
    PositionsEventDto,
    PositionType,
)
from .water_info import WaterAmount, WaterInfoEventDto


@dataclass(frozen=True)
class BatteryEventDto(EventDto):
    """Battery event representation."""

    value: int


class CleanJobStatus(DisplayNameIntEnum):
    """Enum of the different clean job status."""

    CLEANING = -1
    # below the identified stop_reason values
    FINISHED = 1
    MANUAL_STOPPED = 2, "manual stopped"
    FINISHED_WITH_WARNINGS = 3, "finished with warnings"


@dataclass(frozen=True)
class CleanLogEntry:
    """Clean log entry representation."""

    timestamp: int
    image_url: str
    type: str
    area: int
    stop_reason: CleanJobStatus
    duration: int  # in seconds


@dataclass(frozen=True)
class CleanLogEventDto(EventDto):
    """Clean log event representation."""

    logs: List[CleanLogEntry]


@dataclass(frozen=True)
class CustomCommandEventDto(EventDto):
    """Custom command event representation."""

    name: str
    response: Dict[str, Any]


@dataclass(frozen=True)
class ErrorEventDto(EventDto):
    """Error event representation."""

    code: int
    description: Optional[str]


@dataclass(frozen=True)
class FanSpeedEventDto(EventDto):
    """Fan speed event representation."""

    speed: str


@unique
class LifeSpan(str, Enum):
    """Enum class for all possible life span components."""

    SIDE_BRUSH = "sideBrush"
    BRUSH = "brush"
    FILTER = "heap"


@dataclass(frozen=True)
class LifeSpanEventDto(EventDto):
    """Life span event representation."""

    type: LifeSpan
    percent: float


@dataclass(frozen=True)
class MapEventDto(EventDto):
    """Map event representation."""


@dataclass(frozen=True)
class RoomEvent(Room, EventDto):
    """Room event."""


@dataclass(frozen=True)
class RoomsEventDto(EventDto):
    """Room event representation."""

    rooms: List[Room]


@dataclass(frozen=True)
class StatsEventDto(EventDto):
    """Stats event representation."""

    area: Optional[int]
    time: Optional[int]
    type: Optional[str]


@dataclass(frozen=True)
class ReportStatsEventDto(StatsEventDto):
    """Report stats event representation."""

    cleaning_id: str
    status: CleanJobStatus
    rooms: Optional[List[int]]


@dataclass(frozen=True)
class TotalStatsEventDto(EventDto):
    """Total stats event representation."""

    area: int
    time: int
    cleanings: int


@dataclass(frozen=True)
class StatusEventDto(EventDto):
    """Status event representation."""

    available: bool
    state: Optional[VacuumState]


@dataclass(frozen=True)
class VolumeEventDto(EventDto):
    """Volume event."""

    volume: int
    maximum: Optional[int]
