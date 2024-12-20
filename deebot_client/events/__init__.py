"""Events module."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum, unique
from typing import TYPE_CHECKING, Any, Self

from deebot_client.events.base import Event

from .efficiency_mode import EfficiencyMode, EfficiencyModeEvent
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
from .network import NetworkInfoEvent
from .water_info import SweepType, WaterAmount, WaterInfoEvent
from .work_mode import WorkMode, WorkModeEvent

if TYPE_CHECKING:
    from deebot_client.models import Room, State

__all__ = [
    "BatteryEvent",
    "CachedMapInfoEvent",
    "CleanJobStatus",
    "CleanLogEntry",
    "EfficiencyMode",
    "EfficiencyModeEvent",
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
    "NetworkInfoEvent",
    "Position",
    "PositionType",
    "PositionsEvent",
    "SweepModeEvent",
    "SweepType",
    "WaterAmount",
    "WaterInfoEvent",
    "WorkMode",
    "WorkModeEvent",
]


@dataclass(frozen=True)
class BatteryEvent(Event):
    """Battery event representation."""

    value: int


@unique
class CleanJobStatus(IntEnum):
    """Enum of the different clean job status."""

    NO_STATUS = -2
    CLEANING = -1
    # below the identified stop_reason values
    FINISHED = 1
    MANUALLY_STOPPED = 2
    FINISHED_WITH_WARNINGS = 3


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
class LifeSpan(StrEnum):
    """Enum class for all possible life span components."""

    xml_value: str

    def __new__(cls, value: str, xml_value: str = "") -> Self:
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.xml_value = xml_value
        return obj

    @classmethod
    def from_xml(cls, value: str) -> LifeSpan:
        """Get LifeSpan from xml value."""
        for life_span in LifeSpan:
            if life_span.xml_value == value:
                return life_span

        msg = f"{value} is not a valid {cls.__name__}"
        raise ValueError(msg)

    BRUSH = "brush", "Brush"
    FILTER = "heap", "Heap"
    SIDE_BRUSH = "sideBrush", "SideBrush"
    UNIT_CARE = "unitCare", "UnitCare"
    ROUND_MOP = "roundMop", "RoundMop"
    AIR_FRESHENER = "dModule", "DModule"
    UV_SANITIZER = "uv", "Uv"
    HUMIDIFY = "humidify", "Humidify"
    HUMIDIFY_MAINTENANCE = "wbCare", "WbCare"
    BLADE = "blade", "Blade"
    LENS_BRUSH = "lensBrush", "LensBrush"
    DUST_BAG = "dustBag", "DustBag"
    CLEANING_FLUID = "autoWater_cleaningFluid", "AutoWater_cleaningFluid"
    STRAINER = "strainer", "Strainer"
    HAND_FILTER = "handFilter", "HandFilter"
    DUST_CASE_HEAP = "dustCaseHeap", "DustCaseHeap"


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


@dataclass(frozen=True, kw_only=True)
class AvailabilityEvent(Event):
    """Availability event."""

    available: bool


@dataclass(frozen=True)
class OtaEvent(Event):
    """Ota event."""

    support_auto: bool
    auto_enabled: bool | None = None
    version: str | None = None
    status: str | None = None
    progress: int | None = None


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
class TrueDetectEvent(EnableEvent):
    """TrueDetect event."""


@dataclass(frozen=True)
class VoiceAssistantStateEvent(EnableEvent):
    """VoiceAssistantState event."""


@dataclass(frozen=True)
class SweepModeEvent(EnableEvent):
    """SweepMode event ("Mop-Only" option)."""


@dataclass(frozen=True)
class ChildLockEvent(EnableEvent):
    """Child lock event."""


@dataclass(frozen=True)
class BorderSwitchEvent(EnableEvent):
    """Border switch event."""


@dataclass(frozen=True)
class CrossMapBorderWarningEvent(EnableEvent):
    """Cross map border warning event."""


@dataclass(frozen=True)
class MoveUpWarningEvent(EnableEvent):
    """Move up warning event."""


@dataclass(frozen=True)
class SafeProtectEvent(EnableEvent):
    """Safe protect event."""


@dataclass(frozen=True)
class CutDirectionEvent(Event):
    """Cut direction event representation."""

    angle: int
