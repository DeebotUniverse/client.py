"""Hardware device capabilities tests."""


import pytest

from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.clean import GetCleanInfo
from deebot_client.commands.json.life_span import GetLifeSpan
from deebot_client.events import AvailabilityEvent, LifeSpan, LifeSpanEvent, StateEvent
from deebot_client.hardware.device_capabilities import (
    AbstractDeviceCapabilities,
    DeviceCapabilities,
    DeviceCapabilitiesRef,
    convert,
)
from deebot_client.hardware.exceptions import (
    DeviceCapabilitiesRefNotFoundError,
    InvalidDeviceCapabilitiesError,
    RequiredEventMissingError,
)
from tests.helpers import get_device_capabilities


def test_invalid_ref() -> None:
    """Test error is raised if the ref is invalid."""
    device_ref = "not existing"
    device_capbabilities_ref = DeviceCapabilitiesRef("invalid", device_ref)
    devices = {"valid": get_device_capabilities(), "invalid": device_capbabilities_ref}

    with pytest.raises(
        DeviceCapabilitiesRefNotFoundError,
        match=rf'Device ref: "{device_ref}" not found',
    ):
        device_capbabilities_ref.create(devices)


def test_convert_raises_error() -> None:
    """Test if convert raises error for unsporrted class."""

    class _TestCapabilities(AbstractDeviceCapabilities):
        pass

    _class = "abc"
    device_capabilities = _TestCapabilities("test")

    with pytest.raises(
        InvalidDeviceCapabilitiesError,
        match=rf'The class "{_class} has a invalid device capabilities "_TestCapabilities"',
    ):
        convert(_class, device_capabilities, {})


def test_DeviceCapabilites_check_for_required_events() -> None:
    """Test if DevcieCapabilites raises error if not all required events are present."""

    with pytest.raises(
        RequiredEventMissingError,
        match=r'Required event "AvailabilityEvent" is missing.',
    ):
        DeviceCapabilities("test", {})


def test_get_refresh_commands() -> None:
    device_capabilites = DeviceCapabilities(
        "Test",
        {
            AvailabilityEvent: [GetBattery(True)],
            LifeSpanEvent: [(lambda dc: GetLifeSpan(dc.capabilities[LifeSpan]))],
            StateEvent: [GetChargeState(), GetCleanInfo()],
        },
        {LifeSpan: {LifeSpan.BRUSH, LifeSpan.SIDE_BRUSH}},
    )

    assert device_capabilites.get_refresh_commands(AvailabilityEvent) == [
        GetBattery(True)
    ]
    assert device_capabilites.get_refresh_commands(LifeSpanEvent) == [
        GetLifeSpan({LifeSpan.BRUSH, LifeSpan.SIDE_BRUSH})
    ]
    assert device_capabilites.get_refresh_commands(StateEvent) == [
        GetChargeState(),
        GetCleanInfo(),
    ]
