"""Events module."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TYPE_CHECKING, Any

from .base import Event
from .clean import CleanCountEvent, CleanJobStatus, CleanLogEntry, CleanLogEvent
from .efficiency_mode import EfficiencyMode, EfficiencyModeEvent
from .fan_speed import FanSpeedEvent, FanSpeedLevel
from .map import (
    CachedMapInfoEvent,
    MajorMapEvent,
    MapChangedEvent,
    MapInfoEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MapTraceEvent,
    MinorMapEvent,
    Position,
    PositionsEvent,
    PositionType,
)
from .network import NetworkInfoEvent
from .stats import ReportStatsEvent, StatsEvent, TotalStatsEvent
from .water_info import WaterAmount, WaterInfoEvent
from .work_mode import WorkMode, WorkModeEvent

if TYPE_CHECKING:
    from deebot_client.models import Room, State

__all__ = [
    "BatteryEvent",
    "CachedMapInfoEvent",
    "CleanCountEvent",
    "CleanJobStatus",
    "CleanLogEntry",
    "CleanLogEvent",
    "EfficiencyMode",
    "EfficiencyModeEvent",
    "Event",
    "FanSpeedEvent",
    "FanSpeedLevel",
    "MajorMapEvent",
    "MapChangedEvent",
    "MapInfoEvent",
    "MapSetEvent",
    "MapSetType",
    "MapSubsetEvent",
    "MapTraceEvent",
    "MinorMapEvent",
    "NetworkInfoEvent",
    "Position",
    "PositionsEvent",
    "PositionType",
    "ReportStatsEvent",
    "StatsEvent",
    "SweepModeEvent",
    "TotalStatsEvent",
    "WaterAmount",
    "WaterInfoEvent",
    "WorkMode",
    "WorkModeEvent",
]


@dataclass(frozen=True, kw_only=True)
class AvailabilityEvent(Event):
    """Availability event."""

    available: bool


@dataclass(frozen=True)
class BatteryEvent(Event):
    """Battery event representation."""

    value: int


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
    UNIT_CARE = "unitCare"
    ROUND_MOP = "roundMop"
    AIR_FRESHENER = "dModule"
    UV_SANITIZER = "uv"
    HUMIDIFY = "humidify"
    HUMIDIFY_MAINTENANCE = "wbCare"


@dataclass(frozen=True)
class LifeSpanEvent(Event):
    """Life span event representation."""

    type: LifeSpan
    percent: float
    remaining: int  # in minutes


@dataclass(frozen=True)
class OtaEvent(Event):
    """Ota event."""

    support_auto: bool
    auto_enabled: bool | None = None
    version: str | None = None
    status: str | None = None
    progress: int | None = None


@dataclass(frozen=True)
class RoomsEvent(Event):
    """Room event representation."""

    rooms: list[Room]


@dataclass(frozen=True)
class StateEvent(Event):
    """State event representation."""

    state: State


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
class SweepModeEvent(EnableEvent):
    """SweepMode event ("Mop-Only" option)."""


@dataclass(frozen=True)
class TrueDetectEvent(EnableEvent):
    """TrueDetect event."""


@dataclass(frozen=True)
class VoiceAssistantStateEvent(EnableEvent):
    """VoiceAssistantState event."""
