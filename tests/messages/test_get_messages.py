from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.commands.json.error import GetError
from deebot_client.commands.json.map import GetMapSet, GetMapTrace, GetMinorMap
from deebot_client.const import DataType
from deebot_client.messages import get_message
from deebot_client.messages.json.battery import OnBattery
from deebot_client.messages.json.stats import OnStats

if TYPE_CHECKING:
    from deebot_client.message import Message


@pytest.mark.parametrize(
    ("name", "data_type", "expected"),
    [
        ("onBattery", DataType.JSON, OnBattery),
        ("onBattery_V2", DataType.JSON, OnBattery),
        ("onError", DataType.JSON, GetError),
        ("onStats", DataType.JSON, OnStats),
        ("GetCleanLogs", DataType.JSON, None),
        ("unknown", DataType.JSON, None),
        ("unknown", DataType.XML, None),
    ],
)
def test_get_messages(
    name: str, data_type: DataType, expected: type[Message] | None
) -> None:
    """Test get messages."""
    assert get_message(name, data_type) == expected


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
) -> None:
    assert get_message(name, DataType.JSON, has_map=has_map) == expected
