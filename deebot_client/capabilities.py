"""Device capabilities module."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field, fields, is_dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Generic, ParamSpec, TypeVar

from deebot_client.events import (
    AdvancedModeEvent,
    AvailabilityEvent,
    BaseStationAction,
    BaseStationEvent,
    BatteryEvent,
    BorderSwitchEvent,
    CachedMapInfoEvent,
    CarpetAutoFanBoostEvent,
    ChildLockEvent,
    CleanCountEvent,
    CleanLogEvent,
    CleanPreferenceEvent,
    ContinuousCleaningEvent,
    CrossMapBorderWarningEvent,
    CustomCommandEvent,
    CutDirectionEvent,
    ErrorEvent,
    Event,
    FanSpeedEvent,
    FanSpeedLevel,
    LifeSpan,
    LifeSpanEvent,
    MajorMapEvent,
    MapChangedEvent,
    MapTraceEvent,
    MoveUpWarningEvent,
    MultimapStateEvent,
    NetworkInfoEvent,
    OtaEvent,
    PositionsEvent,
    ReportStatsEvent,
    RoomsEvent,
    SafeProtectEvent,
    StateEvent,
    StatsEvent,
    SweepModeEvent,
    TotalStatsEvent,
    TrueDetectEvent,
    VoiceAssistantStateEvent,
    VolumeEvent,
    WaterAmount,
    WaterInfoEvent,
    WorkMode,
    WorkModeEvent,
    auto_empty,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from _typeshed import DataclassInstance

    from deebot_client.command import Command
    from deebot_client.commands.json.common import ExecuteCommand
    from deebot_client.events.efficiency_mode import EfficiencyMode, EfficiencyModeEvent
    from deebot_client.models import CleanAction, CleanMode


_T = TypeVar("_T")
_EVENT = TypeVar("_EVENT", bound=Event)
_P = ParamSpec("_P")


def _get_events(
    capabilities: DataclassInstance | type[DataclassInstance],
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
class CapabilitySet(CapabilityEvent[_EVENT], Generic[_EVENT, _P]):
    """Capability setCommand with event."""

    set: Callable[_P, ExecuteCommand]


@dataclass(frozen=True)
class CapabilitySetEnable(CapabilitySet[_EVENT, [bool]]):
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
class CapabilitySetTypes(CapabilitySet[_EVENT, _P], CapabilityTypes[_T]):
    """Capability for set command and types."""


@dataclass(frozen=True, kw_only=True)
class CapabilityCleanAction:
    """Capabilities for clean action."""

    command: Callable[[CleanAction], Command]
    area: Callable[[CleanMode, str, int], Command] | None = None


@dataclass(frozen=True, kw_only=True)
class CapabilityClean:
    """Capabilities for clean."""

    action: CapabilityCleanAction
    continuous: CapabilitySetEnable[ContinuousCleaningEvent] | None = None
    count: CapabilitySet[CleanCountEvent, [int]] | None = None
    log: CapabilityEvent[CleanLogEvent] | None = None
    preference: CapabilitySetEnable[CleanPreferenceEvent] | None = None
    work_mode: CapabilitySetTypes[WorkModeEvent, [WorkMode | str], WorkMode] | None = (
        None
    )


@dataclass(frozen=True, kw_only=True)
class CapabilityBaseStationAction:
    """Capabilities for base station action."""

    command: Callable[[BaseStationAction], Command]


@dataclass(frozen=True, kw_only=True)
class CapabilityBaseStation:
    """Capabilities for base station."""

    action: CapabilityBaseStationAction
    event: CapabilityEvent[BaseStationEvent] | None = None


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

    cached_info: CapabilityEvent[CachedMapInfoEvent]
    changed: CapabilityEvent[MapChangedEvent]
    clear: CapabilityExecute | None = None
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

    advanced_mode: CapabilitySetEnable[AdvancedModeEvent] | None = None
    carpet_auto_fan_boost: CapabilitySetEnable[CarpetAutoFanBoostEvent] | None = None
    efficiency_mode: (
        CapabilitySetTypes[EfficiencyModeEvent, [EfficiencyMode | str], EfficiencyMode]
        | None
    ) = None
    border_switch: CapabilitySetEnable[BorderSwitchEvent] | None = None
    child_lock: CapabilitySetEnable[ChildLockEvent] | None = None
    cut_direction: CapabilitySet[CutDirectionEvent, [int]] | None = None
    moveup_warning: CapabilitySetEnable[MoveUpWarningEvent] | None = None
    cross_map_border_warning: CapabilitySetEnable[CrossMapBorderWarningEvent] | None = (
        None
    )
    safe_protect: CapabilitySetEnable[SafeProtectEvent] | None = None
    ota: CapabilitySetEnable[OtaEvent] | CapabilityEvent[OtaEvent] | None = None
    sweep_mode: CapabilitySetEnable[SweepModeEvent] | None = None
    true_detect: CapabilitySetEnable[TrueDetectEvent] | None = None
    voice_assistant: CapabilitySetEnable[VoiceAssistantStateEvent] | None = None
    volume: CapabilitySet[VolumeEvent, [int]]


@dataclass(frozen=True, kw_only=True)
class CapabilityStation:
    """Capabilities for station."""

    auto_empty: (
        CapabilitySetTypes[
            auto_empty.AutoEmptyEvent,
            [bool | None, auto_empty.Frequency | str | None],
            auto_empty.Frequency,
        ]
        | None
    ) = None


@dataclass(frozen=True, kw_only=True)
class Capabilities(ABC):
    """Capabilities."""

    device_type: DeviceType = field(kw_only=False)

    availability: CapabilityEvent[AvailabilityEvent]
    base_station: CapabilityBaseStation | None = None
    battery: CapabilityEvent[BatteryEvent]
    charge: CapabilityExecute
    clean: CapabilityClean
    custom: CapabilityCustomCommand[CustomCommandEvent]
    error: CapabilityEvent[ErrorEvent]
    fan_speed: (
        CapabilitySetTypes[FanSpeedEvent, [FanSpeedLevel | str], FanSpeedLevel] | None
    ) = None
    life_span: CapabilityLifeSpan
    map: CapabilityMap | None = None
    network: CapabilityEvent[NetworkInfoEvent]
    play_sound: CapabilityExecute
    settings: CapabilitySettings
    state: CapabilityEvent[StateEvent]
    station: CapabilityStation = field(default_factory=CapabilityStation)
    stats: CapabilityStats
    water: (
        CapabilitySetTypes[WaterInfoEvent, [WaterAmount | str], WaterAmount] | None
    ) = None

    _events: MappingProxyType[type[Event], list[Command]] = field(init=False)

    def __post_init__(self) -> None:
        """Post init."""
        object.__setattr__(self, "_events", _get_events(self))

    def get_refresh_commands(self, event: type[Event]) -> list[Command]:
        """Return refresh command for given event."""
        return self._events.get(event, [])


class DeviceType(StrEnum):
    """Device type."""

    VACUUM = "vacuum"
    MOWER = "mower"
