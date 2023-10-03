"""Deebot hardware exception module."""


from typing import TYPE_CHECKING

from deebot_client.events.base import Event
from deebot_client.exceptions import DeebotError

if TYPE_CHECKING:
    from deebot_client.hardware.device_capabilities import DeviceCapabilities


class HardwareError(DeebotError):
    """Hardware error."""


class DeviceCapabilitiesRefNotFoundError(HardwareError):
    """Device capabilities reference not found error."""

    def __init__(self, ref: str) -> None:
        super().__init__(f'Device ref: "{ref}" not found')


class RequiredEventMissingError(HardwareError):
    """Required event missing error."""

    def __init__(self, event: type["Event"]) -> None:
        super().__init__(f'Required event "{event.__name__}" is missing.')


class InvalidDeviceCapabilitiesError(HardwareError):
    """Invalid device capabilities error."""

    def __init__(self, _class: str, device_cababilities: "DeviceCapabilities") -> None:
        super().__init__(
            f'The class "{_class} has a invalid device capabilities "{device_cababilities.__class__.__name__}"'
        )
