"""Events module."""

from dataclasses import dataclass
from enum import Enum, unique
from typing import Any

from deebot_client.events.base import Event
from deebot_client.models import Room, VacuumState
from deebot_client.util import DisplayNameIntEnum

from .fan_speed import FanSpeedEvent, FanSpeedLevel
from .map import (
    CachedMapInfoEvent,
    MajorMapEvent,
    MapChangedEvent,
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

__all__ = [
    "BatteryEvent",
    "CachedMapInfoEvent",
    "CleanJobStatus",
    "CleanLogEntry",
    "Event",
    "FanSpeedEvent",
    "FanSpeedLevel",
    "MajorMapEvent",
    "MapChangedEvent",
    "MapSetEvent",
    "MapSetType",
    "MapSubsetEvent",
    "MapTraceEvent",
    "MinorMapEvent",
    "Position",
    "PositionType",
    "PositionsEvent",
    "WaterAmount",
    "WaterInfoEvent",
]


@dataclass(frozen=True)
class BatteryEvent(Event):
    """Battery event representation."""

    value: int


class CleanJobStatus(DisplayNameIntEnum):
    """Enum of the different clean job status."""

    NO_STATUS = -2
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

    logs: list[CleanLogEntry]


@dataclass(frozen=True)
class CleanCountEvent(Event):
    """Clean count event representation."""

    count: int


@dataclass(frozen=True)
class CustomCommandEvent(Event):
    """Custom command event representation."""

    name: str
    response: dict[str, Any]


@dataclass(frozen=True)
class ErrorEvent(Event):
    """Error event representation."""

    code: int
    description: str | None


@unique
class LifeSpan(str, Enum):
    """Enum class for all possible life span components."""

    BRUSH = "brush"
    FILTER = "heap"
    SIDE_BRUSH = "sideBrush"


@dataclass(frozen=True)
class LifeSpanEvent(Event):
    """Life span event representation."""

    type: LifeSpan
    percent: float
    remaining: int  # in minutes


@dataclass(frozen=True)
class RoomsEvent(Event):
    """Room event representation."""

    rooms: list[Room]


@dataclass(frozen=True)
class StatsEvent(Event):
    """Stats event representation."""

    area: int | None
    time: int | None
    type: str | None


@dataclass(frozen=True)
class ReportStatsEvent(StatsEvent):
    """Report stats event representation."""

    cleaning_id: str
    status: CleanJobStatus
    content: list[int]


@dataclass(frozen=True)
class TotalStatsEvent(Event):
    """Total stats event representation."""

    area: int
    time: int
    cleanings: int


@dataclass(frozen=True)
class AvailabilityEvent(Event):
    """Availability event."""

    available: bool


@dataclass(frozen=True)
class StateEvent(Event):
    """State event representation."""

    state: VacuumState


@dataclass(frozen=True)
class VolumeEvent(Event):
    """Volume event."""

    volume: int
    maximum: int | None


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


@dataclass(frozen=True)
class CleanPreferenceEvent(EnableEvent):
    """CleanPreference event."""


@dataclass(frozen=True)
class MultimapStateEvent(EnableEvent):
    """Multimap state event."""


@dataclass(frozen=True)
class TrueDetectEvent(EnableEvent):
    """TrueDetect event."""
