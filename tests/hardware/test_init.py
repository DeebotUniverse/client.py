"""Hardware init tests."""


import pytest

from deebot_client.hardware import _DEFAULT, get_device_capabilities
from deebot_client.hardware.deebot import _DEVICES, DEVICES
from deebot_client.hardware.device_capabilities import DeviceCapabilities


@pytest.mark.parametrize(
    "_class, expected",
    [
        ("not_specified", _DEFAULT),
        ("yna5x1", _DEVICES["yna5x1"]),
        (
            "vi829v",
            DeviceCapabilities(_DEVICES["vi829v"].name, DEVICES["yna5x1"].events),
        ),
    ],
)
def test_get_device_capabilities(_class: str, expected: DeviceCapabilities) -> None:
    """Test get_device_capabilities."""
    assert expected == get_device_capabilities(_class)
