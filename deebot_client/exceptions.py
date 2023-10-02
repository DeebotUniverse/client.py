"""Deebot client exception module."""


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deebot_client.events.base import Event
    from deebot_client.hardware.device_capabilities import AbstractDeviceCapabilities


class DeebotError(Exception):
    """Deebot error."""


class AuthenticationError(DeebotError):
    """Authentication error."""


class InvalidAuthenticationError(AuthenticationError):
    """Invalid authentication error."""


class ApiError(DeebotError):
    """Api error."""


class MapError(DeebotError):
    """Map error."""


class DeviceCapabilitiesRefNotFoundError(DeebotError):
    """Device capabilities reference not found error."""

    def __init__(self, ref: str) -> None:
        super().__init__(f'Device ref: "{ref}" not found')


class RequiredEventMissingError(DeebotError):
    """Required event missing error."""

    def __init__(self, event: type["Event"]) -> None:
        super().__init__(f'Required event "{event.__name__}" is missing.')


class InvalidDeviceCapabilitiesError(DeebotError):
    """Invalid device capabilities error."""

    def __init__(
        self, _class: str, device_cababilities: "AbstractDeviceCapabilities"
    ) -> None:
        super().__init__(
            f'The class "{_class} has a invalid device capabilities "{device_cababilities.__class__.__name__}"'
        )
