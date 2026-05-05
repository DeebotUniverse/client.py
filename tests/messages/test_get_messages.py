from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.commands.json.error import GetError
from deebot_client.commands.json.map import GetMapSet, GetMapTrace, GetMinorMap
from deebot_client.const import DataType
from deebot_client.messages import get_message
from deebot_client.messages.json.battery import OnBattery
from deebot_client.messages.json.stats import OnStats
from deebot_client.models import StaticDeviceInfo
from tests import get_static_device_info

if TYPE_CHECKING:
    from deebot_client.message import Message


@pytest.fixture
def static_with_map() -> StaticDeviceInfo:
    """Device with map capability (vacuum yna5xi)."""
    return get_static_device_info("yna5xi")


@pytest.fixture
def static_without_map() -> StaticDeviceInfo:
    """Device without map capability (mower xmp9ds)."""
    return get_static_device_info("xmp9ds")


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("onBattery", OnBattery),
        ("onBattery_V2", OnBattery),
        ("onError", GetError),
        ("onStats", OnStats),
        ("GetCleanLogs", None),
        ("unknown", None),
    ],
)
def test_get_messages(
    name: str, expected: type[Message] | None, static_with_map: StaticDeviceInfo
) -> None:
    """Test get messages."""
    assert get_message(name, static_with_map) == expected


@pytest.mark.parametrize(
    ("name", "has_map", "expected"),
    [
        ("onMapTrace", True, GetMapTrace),
        ("onMapSet", True, GetMapSet),
        ("onMinorMap", True, GetMinorMap),
        ("onMapTrace", False, None),
        ("onMapSet", False, None),
        ("onMinorMap", False, None),
        ("onBattery", False, OnBattery),
        ("onBattery", True, OnBattery),
        ("onError", False, GetError),
    ],
)
def test_get_messages_skips_map_legacy_without_map_capability(
    name: str,
    has_map: bool,
    expected: type[Message] | None,
    static_with_map: StaticDeviceInfo,
    static_without_map: StaticDeviceInfo,
) -> None:
    """Test that map-related legacy fallbacks are skipped when device has no map capability."""
    static = static_with_map if has_map else static_without_map
    assert get_message(name, static) == expected
