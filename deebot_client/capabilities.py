"""Device capabilities module."""
from collections.abc import Callable
from dataclasses import dataclass, field, fields, is_dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from deebot_client.command import Command, SetCommand
from deebot_client.events import (
    AdvancedModeEvent,
    AvailabilityEvent,
    BatteryEvent,
    CachedMapInfoEvent,
    CarpetAutoFanBoostEvent,
    CleanCountEvent,
    CleanLogEvent,
    CleanPreferenceEvent,
    ContinuousCleaningEvent,
    CustomCommandEvent,
    ErrorEvent,
    Event,
    FanSpeedEvent,
    FanSpeedLevel,
    LifeSpan,
    LifeSpanEvent,
    MajorMapEvent,
    MapChangedEvent,
    MapTraceEvent,
    MultimapStateEvent,
    NetworkInfoEvent,
    PositionsEvent,
    ReportStatsEvent,
    RoomsEvent,
    StateEvent,
    StatsEvent,
    TotalStatsEvent,
    TrueDetectEvent,
    VoiceAssistantStateEvent,
    VolumeEvent,
    WaterAmount,
    WaterInfoEvent,
    WorkMode,
    WorkModeEvent,
)
from deebot_client.events.auto_empty import AutoEmptyMode, AutoEmptyModeEvent
from deebot_client.events.efficiency_mode import EfficiencyMode, EfficiencyModeEvent
from deebot_client.models import CleanAction, CleanMode

if TYPE_CHECKING:
    from _typeshed import DataclassInstance


_T = TypeVar("_T")
_EVENT = TypeVar("_EVENT", bound=Event)


def _get_events(
    capabilities: "DataclassInstance",
) -> MappingProxyType[type[Event], list[Command]]:
    events = {}
    for field_ in fields(capabilities):
        if not field_.init:
            continue
        field_value = getattr(capabilities, field_.name)
        if isinstance(field_value, CapabilityEvent):
            events[field_value.event] = field_value.get
        elif is_dataclass(field_value):
            events.update(_get_events(field_value))

    return MappingProxyType(events)


@dataclass(frozen=True)
class CapabilityEvent(Generic[_EVENT]):
    """Capability for an event with get command."""

    event: type[_EVENT]
    get: list[Command]


@dataclass(frozen=True)
class CapabilitySet(CapabilityEvent[_EVENT], Generic[_EVENT, _T]):
    """Capability setCommand with event."""

    set: Callable[[_T], SetCommand]


@dataclass(frozen=True)
class CapabilitySetEnable(CapabilitySet[_EVENT, bool]):
    """Capability for SetEnableCommand with event."""


@dataclass(frozen=True)
class CapabilityExecute:
    """Capability to execute a command."""

    execute: type[Command]


@dataclass(frozen=True, kw_only=True)
class CapabilityTypes(Generic[_T]):
    """Capability to specify types support."""

    types: tuple[_T, ...]


@dataclass(frozen=True, kw_only=True)
class CapabilitySetTypes(CapabilitySet[_EVENT, _T | str], CapabilityTypes[_T]):
    """Capability for set command and types."""


@dataclass(frozen=True, kw_only=True)
class CapabilityCleanAutoEmpty(
    CapabilityEvent[AutoEmptyModeEvent], CapabilityTypes[AutoEmptyMode]
):
    """Capabilities for clean auto empty."""

    set: Callable[[bool, AutoEmptyMode | str | None], SetCommand]


@dataclass(frozen=True, kw_only=True)
class CapabilityCleanAction:
    """Capabilities for clean action."""

    command: Callable[[CleanAction], Command]
    area: Callable[[CleanMode, str, int], Command]


@dataclass(frozen=True, kw_only=True)
class CapabilityClean:
    """Capabilities for clean."""

    auto_empty: CapabilityCleanAutoEmpty | None = None
    action: CapabilityCleanAction
    continuous: CapabilitySetEnable[ContinuousCleaningEvent]
    count: CapabilitySet[CleanCountEvent, int] | None = None
    log: CapabilityEvent[CleanLogEvent] | None = None
    preference: CapabilitySetEnable[CleanPreferenceEvent] | None = None
    work_mode: CapabilitySetTypes[WorkModeEvent, WorkMode] | None = None


@dataclass(frozen=True)
class CapabilityCustomCommand(CapabilityEvent[_EVENT]):
    """Capability custom command."""

    set: Callable[[str, Any], Command]


@dataclass(frozen=True, kw_only=True)
class CapabilityLifeSpan(CapabilityEvent[LifeSpanEvent], CapabilityTypes[LifeSpan]):
    """Capabilities for life span."""

    reset: Callable[[LifeSpan], Command]


@dataclass(frozen=True, kw_only=True)
class CapabilityMap:
    """Capabilities for map."""

    chached_info: CapabilityEvent[CachedMapInfoEvent]
    changed: CapabilityEvent[MapChangedEvent]
    major: CapabilityEvent[MajorMapEvent]
    multi_state: CapabilitySetEnable[MultimapStateEvent]
    position: CapabilityEvent[PositionsEvent]
    relocation: CapabilityExecute
    rooms: CapabilityEvent[RoomsEvent]
    trace: CapabilityEvent[MapTraceEvent]


@dataclass(frozen=True, kw_only=True)
class CapabilityStats:
    """Capabilities for statistics."""

    clean: CapabilityEvent[StatsEvent]
    report: CapabilityEvent[ReportStatsEvent]
    total: CapabilityEvent[TotalStatsEvent]


@dataclass(frozen=True, kw_only=True)
class CapabilitySettings:
    """Capabilities for settings."""

    advanced_mode: CapabilitySetEnable[AdvancedModeEvent]
    carpet_auto_fan_boost: CapabilitySetEnable[CarpetAutoFanBoostEvent]
    efficiency_mode: (
        CapabilitySetTypes[EfficiencyModeEvent, EfficiencyMode] | None
    ) = None
    true_detect: CapabilitySetEnable[TrueDetectEvent] | None = None
    voice_assistant: CapabilitySetEnable[VoiceAssistantStateEvent] | None = None
    volume: CapabilitySet[VolumeEvent, int]


@dataclass(frozen=True, kw_only=True)
class Capabilities:
    """Capabilities."""

    availability: CapabilityEvent[AvailabilityEvent]
    battery: CapabilityEvent[BatteryEvent]
    charge: CapabilityExecute
    clean: CapabilityClean
    custom: CapabilityCustomCommand[CustomCommandEvent]
    error: CapabilityEvent[ErrorEvent]
    fan_speed: CapabilitySetTypes[FanSpeedEvent, FanSpeedLevel]
    life_span: CapabilityLifeSpan
    map: CapabilityMap | None = None
    network: CapabilityEvent[NetworkInfoEvent]
    play_sound: CapabilityExecute
    settings: CapabilitySettings
    state: CapabilityEvent[StateEvent]
    stats: CapabilityStats
    water: CapabilitySetTypes[WaterInfoEvent, WaterAmount]

    _events: MappingProxyType[type[Event], list[Command]] = field(init=False)

    def __post_init__(self) -> None:
        """Post init."""
        object.__setattr__(self, "_events", _get_events(self))

    def get_refresh_commands(self, event: type[Event]) -> list[Command]:
        """Return refresh command for given event."""
        return self._events.get(event, [])
