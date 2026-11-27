"""Tests for native map commands (30001, 30004, 50001/50005/50007/50009)."""

from __future__ import annotations

import copy
from typing import Any
from unittest.mock import Mock

import orjson
import pytest

from deebot_client.commands.json.native_map import GetNativeMapData, NativeMapSwitch
from deebot_client.commands.json.native_map_edit import (
    NativeAddNoMopZone,
    NativeAddVirtualWall,
    NativeDeleteNoMopZone,
    NativeDeleteVirtualWall,
    NativeMapOverlay,
    create_native_map_edit,
    native_add_no_mop_zone,
    native_add_virtual_wall,
    native_delete_no_mop_zone,
    native_delete_virtual_wall,
    native_map_overlay,
    native_merge_rooms,
    native_rename_room,
    native_split_room,
)
from deebot_client.commands.json.native_room_edit import (
    NativeMergeRooms,
    NativeRenameRoom,
    NativeSplitRoom,
)
from deebot_client.event_bus import EventBus
from deebot_client.events import MapSetType
from deebot_client.events.map import NativeMapRefreshEvent
from deebot_client.hardware.cqyi87 import get_device_info
from deebot_client.message import HandlingState
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


def test_native_map_switch_success_and_failed_refresh() -> None:
    event_bus = Mock(spec_set=EventBus)
    event_bus.capabilities = get_device_info().capabilities

    cmd = NativeMapSwitch("4")
    ok_resp = {
        "ret": "ok",
        "resp": {"body": {"code": 0, "data": {"mapId": "4"}}, "msg": "ok"},
    }
    res_ok = cmd._handle_response(event_bus, ok_resp)
    assert res_ok.state == HandlingState.SUCCESS
    assert len(res_ok.requested_commands) == 4
    req_names = [c.NAME for c in res_ok.requested_commands]
    assert req_names == ["30001", "30001", "30001", "30001"]

    fail_resp = {"ret": "ok", "resp": {"body": {"code": 500, "msg": "device error"}}}
    res_fail = cmd._handle_response(event_bus, fail_resp)
    assert res_fail.state == HandlingState.FAILED
    assert len(res_fail.requested_commands) == 0


@pytest.mark.parametrize(
    ("command_cls", "cmd_args", "expected_req_count"),
    [
        (NativeAddVirtualWall, ("m1", [-100, 200, 300, 400]), 2),
        (NativeDeleteVirtualWall, ("m1", 5), 2),
        (NativeAddNoMopZone, ("m1", [-200, 100, -200, -50, 50, -50, 50, 100]), 2),
        (NativeDeleteNoMopZone, ("m1", 6), 2),
        (NativeSplitRoom, ("m1", 1, [100, 200, 300, 400]), 1),
        (NativeMergeRooms, ("m1", [1, 2]), 1),
        (NativeRenameRoom, ("m1", 1, "Bedroom"), 1),
    ],
)
def test_edit_commands_success_and_failed_refresh(
    command_cls: Any, cmd_args: tuple[Any, ...], expected_req_count: int
) -> None:
    event_bus = Mock(spec_set=EventBus)
    event_bus.capabilities = get_device_info().capabilities

    cmd = command_cls(*cmd_args)
    ok_resp = {"ret": "ok", "resp": {"body": {"code": 0, "msg": "ok"}}}
    res_ok = cmd._handle_response(event_bus, ok_resp)
    assert res_ok.state == HandlingState.SUCCESS
    assert len(res_ok.requested_commands) == expected_req_count
    for req in res_ok.requested_commands:
        assert req.NAME == "30001"

    fail_resp = {"ret": "ok", "resp": {"body": {"code": 500, "msg": "device error"}}}
    res_fail = cmd._handle_response(event_bus, fail_resp)
    assert res_fail.state == HandlingState.FAILED
    assert len(res_fail.requested_commands) == 0


def test_mm_adapted_cm_factories() -> None:
    wall = native_add_virtual_wall("m1", [-1000, 2000, 3000, 4000])
    assert isinstance(wall._args, dict)
    assert wall._args["point"] == "-100,200,300,400"

    del_wall = native_delete_virtual_wall("m1", 9)
    assert isinstance(del_wall._args, dict)
    assert del_wall._args == {"action": "del", "mode": 1, "mapId": "m1", "id": 9}

    zone = native_add_no_mop_zone(
        "m1", [-2000, 1000, -2000, -500, 500, -500, 500, 1000]
    )
    assert isinstance(zone._args, dict)
    assert zone._args["point"] == "-200,100,-200,-50,50,-50,50,100"

    del_zone = native_delete_no_mop_zone("m1", 12)
    assert isinstance(del_zone._args, dict)
    assert del_zone._args == {"action": "del", "mode": 2, "mapId": "m1", "id": 12}

    split = native_split_room("m1", 3, [1000, 2000, 3000, 4000])
    assert isinstance(split._args, dict)
    assert split._args["points"] == "100,200,300,400"

    merge = native_merge_rooms("m1", [3, 4])
    assert isinstance(merge._args, dict)
    assert merge._args == {"mapId": "m1", "roomIds": [3, 4]}

    rename = native_rename_room("m1", 3, "Kitchen")
    assert isinstance(rename._args, dict)
    assert rename._args == {"mapId": "m1", "roomId": 3, "name": "Kitchen"}


def test_capability_map_edit_bundle() -> None:
    edit_bundle = create_native_map_edit()
    assert edit_bundle.add_virtual_wall is native_add_virtual_wall
    assert edit_bundle.delete_virtual_wall is native_delete_virtual_wall
    assert edit_bundle.add_no_mop_zone is native_add_no_mop_zone
    assert edit_bundle.delete_no_mop_zone is native_delete_no_mop_zone
    assert edit_bundle.split_room is native_split_room
    assert edit_bundle.merge_rooms is native_merge_rooms
    assert edit_bundle.rename_room is native_rename_room

    wall_cmd = edit_bundle.add_virtual_wall("m1", [1000, 2000, 3000, 4000])
    assert isinstance(wall_cmd._args, dict)
    assert wall_cmd._args["point"] == "100,200,300,400"


def test_generic_overlay_adapter() -> None:
    wall = native_map_overlay(
        "add", MapSetType.VIRTUAL_WALLS, "m1", [1000, 2000, 3000, 4000]
    )
    assert isinstance(wall._args, dict)
    assert wall._args["point"] == "100,200,300,400"


def test_native_switch_mqtt_reconstruction_and_reply() -> None:
    raw = orjson.dumps({"body": {"data": {"mapId": "2", "request": "mapSwitch"}}})
    restored = NativeMapSwitch.create_from_mqtt(raw)
    assert restored == NativeMapSwitch("2")

    event_bus = Mock(spec_set=EventBus)
    event_bus.capabilities = get_device_info().capabilities
    cmd = NativeMapSwitch("2")
    cmd.handle_mqtt_p2p(event_bus, orjson.dumps({"body": {"code": 0, "msg": "ok"}}))
    event_bus.request_refresh.assert_called_once()
    event_bus.reset_mock()
    cmd.handle_mqtt_p2p(event_bus, orjson.dumps({"body": {"code": 500, "msg": "fail"}}))
    event_bus.request_refresh.assert_not_called()


def test_native_overlay_mqtt_reconstruction_and_reply() -> None:
    raw_add = orjson.dumps(
        {
            "body": {
                "data": {
                    "action": "add",
                    "mode": 1,
                    "type": 1,
                    "mapId": "m1",
                    "point": "1,2,3,4",
                }
            }
        }
    )
    restored = NativeMapOverlay.create_from_mqtt(raw_add)
    assert restored == NativeMapOverlay(
        "add", MapSetType.VIRTUAL_WALLS, "m1", [1, 2, 3, 4]
    )

    raw_del = orjson.dumps(
        {"body": {"data": {"action": "del", "mode": 2, "mapId": "m1", "id": 7}}}
    )
    restored_del = NativeMapOverlay.create_from_mqtt(raw_del)
    assert restored_del == NativeMapOverlay("del", MapSetType.NO_MOP_ZONES, "m1", 7)

    event_bus = Mock(spec_set=EventBus)
    cmd = NativeAddVirtualWall("m1", [1, 2, 3, 4])
    cmd.handle_mqtt_p2p(event_bus, orjson.dumps({"body": {"code": 0, "msg": "ok"}}))
    event_bus.notify.assert_called_once()
    refresh = event_bus.notify.call_args.args[0]
    assert isinstance(refresh, NativeMapRefreshEvent)
    assert refresh.map_id == "m1"
    event_bus.reset_mock()
    cmd.handle_mqtt_p2p(event_bus, orjson.dumps({"body": {"code": 500, "msg": "fail"}}))
    event_bus.request_refresh.assert_not_called()
    event_bus.notify.assert_not_called()


def test_native_room_edit_mqtt_reconstruction_and_reply() -> None:
    raw_split = orjson.dumps(
        {"body": {"data": {"mapId": "m1", "roomId": 3, "points": "1,2,3,4"}}}
    )
    assert NativeSplitRoom.create_from_mqtt(raw_split) == NativeSplitRoom(
        "m1", 3, [1, 2, 3, 4]
    )
    raw_merge = orjson.dumps({"body": {"data": {"mapId": "m1", "roomIds": [3, 4]}}})
    assert NativeMergeRooms.create_from_mqtt(raw_merge) == NativeMergeRooms(
        "m1", [3, 4]
    )
    raw_rename = orjson.dumps(
        {"body": {"data": {"mapId": "m1", "roomId": 3, "name": "Kitchen"}}}
    )
    assert NativeRenameRoom.create_from_mqtt(raw_rename) == NativeRenameRoom(
        "m1", 3, "Kitchen"
    )

    event_bus = Mock(spec_set=EventBus)
    for cmd in (
        NativeSplitRoom("m1", 3, [1, 2, 3, 4]),
        NativeMergeRooms("m1", [3, 4]),
        NativeRenameRoom("m1", 3, "Kitchen"),
    ):
        cmd.handle_mqtt_p2p(event_bus, orjson.dumps({"body": {"code": 0, "msg": "ok"}}))
        event_bus.notify.assert_called_once()
        refresh = event_bus.notify.call_args.args[0]
        assert isinstance(refresh, NativeMapRefreshEvent)
        assert refresh.map_id == "m1"
        event_bus.reset_mock()
        cmd.handle_mqtt_p2p(
            event_bus, orjson.dumps({"body": {"code": 500, "msg": "fail"}})
        )
        event_bus.request_refresh.assert_not_called()
        event_bus.notify.assert_not_called()


def test_get_native_map_data_parses_once_without_mutating_response() -> None:
    event_bus = Mock(spec_set=EventBus)
    event_bus.capabilities = get_device_info().capabilities
    cmd = GetNativeMapData.get_map("9")
    resp: dict[str, Any] = {
        "ret": "ok",
        "resp": {
            "body": {
                "code": 0,
                "data": {
                    "mapInfos": [
                        {
                            "angle": 0,
                            "index": 1,
                            "mapId": "9",
                            "name": "M",
                            "saved": 1,
                            "status": 1,
                        }
                    ],
                    "areas": [],
                },
            },
        },
    }
    frozen = copy.deepcopy(resp)
    result = cmd._handle_response(event_bus, resp)
    assert result.state == HandlingState.SUCCESS
    assert resp == frozen
    assert event_bus.notify.call_count == 2


def test_edit_inactive_map_ack_targets_edited_map() -> None:
    event_bus = Mock(spec_set=EventBus)
    event_bus.capabilities = get_device_info().capabilities
    ok: dict[str, Any] = {"ret": "ok", "resp": {"body": {"code": 0, "msg": "ok"}}}
    edit = NativeAddVirtualWall("3", [1, 2, 3, 4])
    result = edit._handle_response(event_bus, ok)
    assert result.state == HandlingState.SUCCESS
    fetched = [
        command.map_id
        for command in result.requested_commands
        if isinstance(command, GetNativeMapData)
    ]
    assert fetched
    assert all(map_id == "3" for map_id in fetched)
