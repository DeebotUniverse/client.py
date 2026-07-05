from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.commands.json.error import GetError
from deebot_client.messages import get_message
from deebot_client.messages.json.battery import OnBattery
from deebot_client.messages.json.stats import OnStats

if TYPE_CHECKING:
    from deebot_client.message import Message
    from deebot_client.models import StaticDeviceInfo


@pytest.mark.parametrize(
    ("device_class", "name", "expected"),
    [
        ("yna5xi", "onBattery", OnBattery),
        ("qhe2o2", "onBattery_V2", OnBattery),
        ("yna5xi", "onError", GetError),
        ("yna5xi", "onStats", OnStats),
        ("yna5xi", "GetCleanLogs", None),
        ("yna5xi", "unknown", None),
        ("2pv572", "unknown", None),
        ("xmp9ds", "onMapTrace", None),
        ("xmp9ds", "onMapSet", None),
        ("xmp9ds", "onMinorMap", None),
        ("xmp9ds", "onBattery", OnBattery),
    ],
)
def test_get_messages(
    static_device_info: StaticDeviceInfo, name: str, expected: type[Message] | None
) -> None:
    """Test get messages."""
    assert get_message(name, static_device_info) == expected
