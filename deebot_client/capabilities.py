"""Device capabilities module."""
from collections.abc import Callable
from dataclasses import dataclass, field, fields, is_dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Generic, TypeVar

from deebot_client.command import Command
from deebot_client.commands.json.common import SetCommand, SetEnableCommand
from deebot_client.events import LifeSpan
from deebot_client.events.base import Event
from deebot_client.events.water_info import WaterAmount

if TYPE_CHECKING:
    from _typeshed import DataclassInstance


_T = TypeVar("_T")


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
class CapabilityEvent:
    """Capability for an event with get command."""

    event: type[Event]
    get: list[Command]


@dataclass(frozen=True)
class CapabilitySet(CapabilityEvent, Generic[_T]):
    """Capability setCommand with event."""

    set: Callable[[_T], SetCommand]


@dataclass(frozen=True)
class CapabilitySetEnable(CapabilitySet[bool]):
    """Capability for SetEnableCommand with event."""

    set: Callable[[bool], SetEnableCommand]


@dataclass(frozen=True)
class CapabilityExecute:
    """Capability to execute a command."""

    execute: type[Command]


@dataclass(frozen=True, kw_only=True)
class CapabilityCleanAction:
    """Capabilities for clean action."""

    command: type[Command]
    area: type[Command]


@dataclass(frozen=True, kw_only=True)
class CapabilityClean:
    """Capabilities for clean."""

    action: CapabilityCleanAction
    continuous: CapabilitySetEnable
    count: CapabilitySet[int] | None = None
    log: CapabilityEvent
    preference: CapabilitySetEnable | None = None


@dataclass(frozen=True, kw_only=True)
class CapabilityLifeSpan(CapabilityEvent):
    """Capabilities for life span."""

    types: set[LifeSpan]
    reset: Callable[[LifeSpan], Command]


@dataclass(frozen=True, kw_only=True)
class CapabilityMap:
    """Capabilities for map."""

    chached_info: CapabilityEvent
    major: CapabilityEvent
    multi_state: CapabilitySetEnable
    position: CapabilityEvent
    relocation: CapabilityExecute
    rooms: CapabilityEvent
    trace: CapabilityEvent


@dataclass(frozen=True, kw_only=True)
class CapabilityStats:
    """Capabilities for statistics."""

    clean: CapabilityEvent
    total: CapabilityEvent


@dataclass(frozen=True, kw_only=True)
class CapabilitySettings:
    """Capabilities for settings."""

    advanced_mode: CapabilitySetEnable
    carpet_auto_fan_boost: CapabilitySetEnable
    true_detect: CapabilitySetEnable | None = None
    volume: CapabilitySet[int]


@dataclass(frozen=True, kw_only=True)
class Capabilities:
    """Capabilities."""

    availability: CapabilityEvent
    battery: CapabilityEvent
    charge: CapabilityExecute
    clean: CapabilityClean
    error: CapabilityEvent
    fan_speed: CapabilitySet
    life_span: CapabilityLifeSpan
    map: CapabilityMap
    play_sound: CapabilityExecute
    settings: CapabilitySettings
    state: CapabilityEvent
    stats: CapabilityStats
    water: CapabilitySet[WaterAmount]

    _events: MappingProxyType[type[Event], list[Command]] = field(init=False)

    def __post_init__(self) -> None:
        """Post init."""
        object.__setattr__(self, "_events", _get_events(self))

    def get_refresh_commands(self, event: type[Event]) -> list[Command]:
        """Return refresh command for given event."""
        return self._events.get(event, [])
