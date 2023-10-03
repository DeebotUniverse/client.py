"""Device module."""
from abc import ABC
from collections.abc import Mapping
from dataclasses import dataclass

from deebot_client.command import Command
from deebot_client.events import AvailabilityEvent, CustomCommandEvent, ReportStatsEvent
from deebot_client.events.base import Event
from deebot_client.events.map import MapSetEvent, MapSubsetEvent, MinorMapEvent

from .exceptions import (
    DeviceCapabilitiesRefNotFoundError,
    InvalidDeviceCapabilitiesError,
    RequiredEventMissingError,
)

_COMMON_NO_POLL_EVENTS = [
    CustomCommandEvent,
    MapSetEvent,
    MapSubsetEvent,
    MinorMapEvent,
    ReportStatsEvent,
]

_REQUIRED_EVENTS = [AvailabilityEvent]


@dataclass(frozen=True)
class AbstractDeviceCapabilities(ABC):
    """Abstract device capabilities."""

    name: str


@dataclass(frozen=True)
class DeviceCapabilities(AbstractDeviceCapabilities):
    """Device capabilities."""

    events: Mapping[type[Event], list[Command]]

    def __post_init__(self) -> None:
        events = {**self.events}
        for event in _COMMON_NO_POLL_EVENTS:
            events.setdefault(event, [])

        object.__setattr__(self, "capabilities", events)

        for event in _REQUIRED_EVENTS:
            if event not in events:
                raise RequiredEventMissingError(event)

    def get_refresh_commands(self, event: type[Event]) -> list[Command]:
        """Return refresh command for given event."""
        return self.events.get(event, [])


@dataclass(frozen=True)
class DeviceCapabilitiesRef(AbstractDeviceCapabilities):
    """Device capabilitie referring another device."""

    ref: str

    def create(
        self, devices: Mapping[str, AbstractDeviceCapabilities]
    ) -> DeviceCapabilities:
        """Create and return device capbabilities."""
        if (device := devices.get(self.ref)) and isinstance(device, DeviceCapabilities):
            return DeviceCapabilities(self.name, device.events)

        raise DeviceCapabilitiesRefNotFoundError(self.ref)


def convert(
    _class: str,
    device: AbstractDeviceCapabilities,
    devices: Mapping[str, AbstractDeviceCapabilities],
) -> DeviceCapabilities:
    """Convert the device into a device capbabilities."""
    if isinstance(device, DeviceCapabilities):
        return device

    if isinstance(device, DeviceCapabilitiesRef):
        return device.create(devices)

    raise InvalidDeviceCapabilitiesError(_class, device)