"""Device module."""
from collections.abc import Mapping
from dataclasses import dataclass

from deebot_client.command import Command
from deebot_client.events import AvailabilityEvent, CustomCommandEvent, ReportStatsEvent
from deebot_client.events.base import Event
from deebot_client.events.map import MapSetEvent, MapSubsetEvent, MinorMapEvent
from deebot_client.exceptions import DeebotError

_COMMON_NO_POLL_EVENTS = [
    CustomCommandEvent,
    MapSetEvent,
    MapSubsetEvent,
    MinorMapEvent,
    ReportStatsEvent,
]

_REQUIRED_EVENTS = [AvailabilityEvent]


@dataclass(frozen=True)
class _BaseDeviceCapabilities:
    name: str


@dataclass(frozen=True)
class DeviceCapabilities(_BaseDeviceCapabilities):
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

    def is_supported(self, event: type[Event]) -> bool:
        """Return True if event is supported."""
        return event in self.events

    def get_refresh_commands(self, event: type[Event]) -> list[Command]:
        """Return refresh command for given event."""
        return self.events.get(event, [])


@dataclass(frozen=True)
class DeviceCapabilitiesRef(_BaseDeviceCapabilities):
    """Device capabilitie referring another device."""

    ref: str

    def create(self, devices: Mapping[str, DeviceCapabilities]) -> DeviceCapabilities:
        """Create and return device capbabilities."""
        if device := devices.get(self.ref):
            return DeviceCapabilities(self.name, device.events)

        raise ReferanceNotFoundError(self.ref)


class ReferanceNotFoundError(DeebotError):
    """Device reference not found error."""

    def __init__(self, ref: str) -> None:
        super().__init__(f'Device ref: "{ref}" not found')


class RequiredEventMissingError(DeebotError):
    """Required event missing error."""

    def __init__(self, event: type[Event]) -> None:
        super().__init__(f'Required event "{event.__name__}" is missing.')
