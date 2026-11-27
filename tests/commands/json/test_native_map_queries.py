"""Tests for native map queries and map switching."""

from __future__ import annotations

import pytest

from deebot_client.commands.json.native_map import GetNativeMapData, NativeMapSwitch
from tests.commands.json import assert_execute_command


def test_get_native_map_data_constructors() -> None:
    cat = GetNativeMapData.get_catalog()
    assert cat.NAME == "30001"
    assert cat._args == {"fields": ["mapInfos"]}
    assert cat.map_id is None

    status = GetNativeMapData.get_status()
    assert status._args == {"fields": ["mapStatus"]}

    map_cmd = GetNativeMapData.get_map("10")
    assert map_cmd._args == {"fields": ["mapData", "areas", "pos"], "mapId": "10"}
    assert map_cmd.map_id == "10"

    trace_cmd = GetNativeMapData.get_traces("10")
    assert trace_cmd._args == {"fields": ["mapTraceData"], "mapId": "10"}

    overlay_cmd = GetNativeMapData.get_overlays("10")
    assert overlay_cmd._args == {
        "fields": ["virtualWalls", "mopWalls", "carpets"],
        "mapId": "10",
    }


def test_get_native_map_data_validation() -> None:
    with pytest.raises(ValueError, match="non-empty sequence"):
        GetNativeMapData([])
    with pytest.raises(ValueError, match="non-empty string"):
        GetNativeMapData(["mapInfos"], "")


async def test_native_map_switch_wire_payload() -> None:
    cmd = NativeMapSwitch("2")
    assert cmd.NAME == "30004"
    assert cmd._args == {"mapId": "2", "request": "mapSwitch"}
    await assert_execute_command(cmd, {"mapId": "2", "request": "mapSwitch"})


def test_native_map_switch_validation() -> None:
    with pytest.raises(ValueError, match="non-empty string"):
        NativeMapSwitch("")
    with pytest.raises(ValueError, match="non-empty string"):
        NativeMapSwitch("   ")
