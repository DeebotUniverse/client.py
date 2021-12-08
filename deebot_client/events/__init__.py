"""Events module."""

from dataclasses import dataclass
from enum import Enum, unique
from typing import Any, Dict, List, Optional

from ..events.base import Event
from ..models import Room, VacuumState
from ..util import DisplayNameIntEnum
from .map import (
    MajorMapEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MapTraceEvent,
    MinorMapEvent,
    Position,
    PositionsEvent,
    PositionType,
)
from .water_info import WaterAmount, WaterInfoEvent


@dataclass(frozen=True)
class BatteryEvent(Event):
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
class CleanLogEvent(Event):
    """Clean log event representation."""

    logs: List[CleanLogEntry]


@dataclass(frozen=True)
class CustomCommandEvent(Event):
    """Custom command event representation."""

    name: str
    response: Dict[str, Any]


@dataclass(frozen=True)
class ErrorEvent(Event):
    """Error event representation."""

    code: int
    description: Optional[str]


@dataclass(frozen=True)
class FanSpeedEvent(Event):
    """Fan speed event representation."""

    speed: str


@unique
class LifeSpan(str, Enum):
    """Enum class for all possible life span components."""

    SIDE_BRUSH = "sideBrush"
    BRUSH = "brush"
    FILTER = "heap"


@dataclass(frozen=True)
class LifeSpanEvent(Event):
    """Life span event representation."""

    type: LifeSpan
    percent: float
    remaining: int  # in minutes


@dataclass(frozen=True)
class RoomsEvent(Event):
    """Room event representation."""

    rooms: List[Room]


@dataclass(frozen=True)
class StatsEvent(Event):
    """Stats event representation."""

    area: Optional[int]
    time: Optional[int]
    type: Optional[str]


@dataclass(frozen=True)
class ReportStatsEvent(StatsEvent):
    """Report stats event representation."""

    cleaning_id: str
    status: CleanJobStatus
    content: Optional[List[int]]


@dataclass(frozen=True)
class TotalStatsEvent(Event):
    """Total stats event representation."""

    area: int
    time: int
    cleanings: int


@dataclass(frozen=True)
class StatusEvent(Event):
    """Status event representation."""

    available: bool
    state: Optional[VacuumState]


@dataclass(frozen=True)
class VolumeEvent(Event):
    """Volume event."""

    volume: int
    maximum: Optional[int]


@dataclass(frozen=True)
class EnableEvent(Event):
    """Enabled event."""

    enable: bool


@dataclass(frozen=True)
class AdvancedModeEvent(EnableEvent):
    """Advanced mode event."""


@dataclass(frozen=True)
class ContinuousCleaningEvent(EnableEvent):
    """Continuous cleaning event."""


@dataclass(frozen=True)
class CarpetAutoFanBoostEvent(EnableEvent):
    """Carpet pressure event."""
