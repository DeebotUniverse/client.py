"""Hardware device capabilities tests."""


import pytest

from deebot_client.exceptions import DeviceCapabilitiesRefNotFoundError
from deebot_client.hardware.deebot import DEVICES
from deebot_client.hardware.device_capabilities import DeviceCapabilitiesRef
from tests.helpers import get_device_capabilities

from . import verify_sorted_devices


def test_invalid_ref() -> None:
    """Test error is raised if the ref is invalid."""
    device_ref = "not existing"
    device_capbabilities_ref = DeviceCapabilitiesRef("invalid", device_ref)
    devices = {"valid": get_device_capabilities(), "invalid": device_capbabilities_ref}

    with pytest.raises(DeviceCapabilitiesRefNotFoundError) as err:
        device_capbabilities_ref.create(devices)

    assert device_ref in str(err.value)


def test_sorted() -> None:
    """Test if all devices are sorted correctly."""
    verify_sorted_devices(DEVICES)
