"""Events module."""

from dataclasses import dataclass
from enum import Enum, unique
from typing import Any, Dict, List, Optional

from ..events.base import EventDto
from ..models import Room, VacuumState
from ..util import DisplayNameIntEnum
from .water_info import WaterAmount, WaterInfoEventDto


@dataclass(frozen=True)
class BatteryEventDto(EventDto):
    """Battery event representation."""

    value: int


@dataclass(frozen=True)
class CleanLogEntry:
    """Clean log entry representation."""

    timestamp: Optional[int]
    image_url: Optional[str]
    type: Optional[str]
    area: Optional[int]
    stop_reason: Optional[str]
    # Stop reason
    # 1 -> finished
    # 2 -> manual stopped
    # 3 -> finished with warnings (ex. a scheduled room was not cleaned)
    total_time: Optional[int]  # in seconds


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
class RoomsEventDto(EventDto):
    """Room event representation."""

    rooms: List[Room]


@dataclass(frozen=True)
class StatsEventDto(EventDto):
    """Stats event representation."""

    area: Optional[int]
    clean_id: Optional[str]
    time: Optional[int]
    type: Optional[str]
    start: Optional[int]


class CleanJobStopReason(DisplayNameIntEnum):
    """Enum of the different clean job stop reasons."""

    FINISHED = 1
    MANUAL_STOPPED = 2, "manual stopped"
    FINISHED_WITH_WARNINGS = 3, "finished with warnings"


@dataclass(frozen=True)
class ReportStatsEventDto(StatsEventDto):
    """Report stats event representation."""

    stop_reason: CleanJobStopReason
    rooms: List[int]


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

    value: int
    maximum: int
