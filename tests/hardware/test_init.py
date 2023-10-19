"""Hardware init tests."""


import pytest

from deebot_client.hardware import _DEFAULT, get_device_capabilities
from deebot_client.hardware.deebot import _DEVICES, DEVICES
from deebot_client.hardware.device_capabilities import DeviceCapabilities

from . import verify_get_refresh_commands


@pytest.mark.parametrize(
    ("class_", "expected"),
    [
        ("not_specified", _DEFAULT),
        ("yna5x1", _DEVICES["yna5x1"]),
        (
            "vi829v",
            DeviceCapabilities(
                _DEVICES["vi829v"].name,
                DEVICES["yna5x1"].events,
                DEVICES["yna5x1"].capabilities,
            ),
        ),
    ],
)
def test_get_device_capabilities(class_: str, expected: DeviceCapabilities) -> None:
    """Test get_device_capabilities."""
    device_capabilities = get_device_capabilities(class_)
    assert expected == device_capabilities
    verify_get_refresh_commands(device_capabilities)
