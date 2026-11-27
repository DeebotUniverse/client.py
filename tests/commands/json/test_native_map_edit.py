from __future__ import annotations

import re
from typing import Any

import pytest

from deebot_client.commands.json.native_map_edit import (
    NativeAddNoMopZone,
    NativeAddVirtualWall,
    NativeDeleteNoMopZone,
    NativeDeleteVirtualWall,
    NativeMapOverlay,
    NativeMergeRooms,
    NativeRenameRoom,
    NativeSplitRoom,
)
from deebot_client.events import MapSetType
from tests.commands.json import assert_execute_command


def _verify_header(payload: dict[str, Any]) -> None:
    header = payload["header"]
    assert header["pri"] == 3
    assert header["m"] == "cloudctl"
    assert header["channel"] == "rop"
    assert header["ver"] == "0.0.1"
    assert header["tzm"] == 480
    assert isinstance(header["ts"], str)
    assert re.fullmatch(r"\d{13}", header["ts"]) is not None


@pytest.mark.parametrize(
    ("command", "name", "args"),
    [
        (
            NativeAddVirtualWall("map_1", [-100, 200, 300, 400]),
            "50001",
            {
                "action": "add",
                "mode": 1,
                "type": 1,
                "mapId": "map_1",
                "point": "-100,200,300,400",
            },
        ),
        (
            NativeDeleteVirtualWall("map_1", 10),
            "50001",
            {"action": "del", "mode": 1, "mapId": "map_1", "id": 10},
        ),
        (
            NativeAddNoMopZone("map_1", [-200, 100, -200, -50, 50, -50, 50, 100]),
            "50001",
            {
                "action": "add",
                "mode": 2,
                "type": 2,
                "mapId": "map_1",
                "point": "-200,100,-200,-50,50,-50,50,100",
            },
        ),
        (
            NativeDeleteNoMopZone("map_1", 20),
            "50001",
            {"action": "del", "mode": 2, "mapId": "map_1", "id": 20},
        ),
        (
            NativeSplitRoom("map_1", 5, [100, 200, 300, 400]),
            "50005",
            {"mapId": "map_1", "roomId": 5, "points": "100,200,300,400"},
        ),
        (
            NativeMergeRooms("map_1", [5, 6]),
            "50007",
            {"mapId": "map_1", "roomIds": [5, 6]},
        ),
        (
            NativeRenameRoom("map_1", 5, "Living Room"),
            "50009",
            {"mapId": "map_1", "roomId": 5, "name": "Living Room"},
        ),
    ],
)
async def test_native_map_edit_wire_payloads(
    command: Any, name: str, args: dict[str, Any]
) -> None:
    assert name == command.NAME
    payload = command._get_payload()
    assert isinstance(payload, dict)
    _verify_header(payload)
    assert payload["body"] == {"data": args}
    await assert_execute_command(command, args)


def test_native_map_overlay_shared_dispatcher_and_factories() -> None:
    wall = NativeAddVirtualWall("m1", [-1000, 2000, 3000, 4000], in_mm=True)
    assert isinstance(wall, NativeMapOverlay)
    assert isinstance(wall._args, dict)
    assert wall._args["point"] == "-100,200,300,400"

    del_wall = NativeDeleteVirtualWall("m1", 3)
    assert isinstance(del_wall, NativeMapOverlay)
    assert del_wall._args == {"action": "del", "mode": 1, "mapId": "m1", "id": 3}

    zone = NativeAddNoMopZone(
        "m1", [-2000, 1000, -2000, -500, 500, -500, 500, 1000], in_mm=True
    )
    assert isinstance(zone, NativeMapOverlay)
    assert isinstance(zone._args, dict)
    assert zone._args["point"] == "-200,100,-200,-50,50,-50,50,100"

    del_zone = NativeDeleteNoMopZone("m1", 4)
    assert isinstance(del_zone, NativeMapOverlay)
    assert del_zone._args == {"action": "del", "mode": 2, "mapId": "m1", "id": 4}


@pytest.mark.parametrize(
    ("map_id", "coords", "err"),
    [
        ("", [100, 200, 300, 400], "map_id must be a non-empty string"),
        ("   ", [100, 200, 300, 400], "map_id must be a non-empty string"),
        ("m1", [100, 200, 300], "exactly 4 coordinates"),
        ("m1", [100, 200, 100, 200], "cannot be degenerate"),
        ("m1", [float("nan"), 200, 300, 400], "must be finite"),
    ],
)
def test_native_add_virtual_wall_invalid_inputs(
    map_id: str, coords: list[float], err: str
) -> None:
    with pytest.raises(ValueError, match=err):
        NativeAddVirtualWall(map_id, coords)


@pytest.mark.parametrize(
    "invalid_id",
    [True, False, "1", None],
)
def test_native_overlay_delete_invalid_ids(invalid_id: Any) -> None:
    with pytest.raises(TypeError, match="non-boolean integer"):
        NativeDeleteVirtualWall("m1", invalid_id)


def test_native_overlay_unsupported_kind() -> None:
    with pytest.raises(ValueError, match="Unsupported kind"):
        NativeMapOverlay("add", MapSetType.ROOMS, "m1", [1, 2, 3, 4])


def test_native_overlay_unsupported_action() -> None:
    with pytest.raises(ValueError, match="Unsupported action"):
        NativeMapOverlay("modify", MapSetType.VIRTUAL_WALLS, "m1", [1, 2, 3, 4])


@pytest.mark.parametrize(
    ("coords", "err"),
    [
        ([1, 2, 3, 4], "at least 3 points"),
        ([1, 2, 3, 4, 5], "even length"),
        ([10, 20, 10, 20, 10, 20], "cannot be degenerate"),
    ],
)
def test_native_add_no_mop_zone_invalid(coords: list[int], err: str) -> None:
    with pytest.raises(ValueError, match=err):
        NativeAddNoMopZone("m1", coords)


@pytest.mark.parametrize(
    ("map_id", "room_id", "points", "err"),
    [
        ("", 1, [100, 200, 300, 400], "map_id must be a non-empty string"),
        ("m1", True, [100, 200, 300, 400], "Room ID must be a non-boolean integer"),
        ("m1", 1, [100, 200, 300], "exactly 4 coordinates"),
        ("m1", 1, [100, 200, 100, 200], "cannot be degenerate"),
    ],
)
def test_native_split_room_invalid(
    map_id: str, room_id: Any, points: list[int], err: str
) -> None:
    with pytest.raises((ValueError, TypeError), match=err):
        NativeSplitRoom(map_id, room_id, points)


def test_native_split_room_mm_conversion() -> None:
    cmd = NativeSplitRoom("m1", 2, [1000, 2000, 3000, 4000], in_mm=True)
    assert isinstance(cmd._args, dict)
    assert cmd._args["points"] == "100,200,300,400"


@pytest.mark.parametrize(
    ("map_id", "room_ids", "err"),
    [
        ("", [1, 2], "map_id must be a non-empty string"),
        ("m1", [1], "requires exactly 2 room IDs"),
        ("m1", [1, 2, 3], "requires exactly 2 room IDs"),
        ("m1", [2, 2], "Merge room IDs must be distinct"),
        ("m1", [True, 2], "Room ID 1 must be a non-boolean integer"),
    ],
)
def test_native_merge_rooms_invalid(map_id: str, room_ids: list[Any], err: str) -> None:
    with pytest.raises((ValueError, TypeError), match=err):
        NativeMergeRooms(map_id, room_ids)


@pytest.mark.parametrize(
    ("map_id", "room_id", "name", "err"),
    [
        ("", 1, "Kitchen", "map_id must be a non-empty string"),
        ("m1", False, "Kitchen", "Room ID must be a non-boolean integer"),
        ("m1", 1, "", "Room name must be a non-empty string"),
        ("m1", 1, "   ", "Room name must be a non-empty string"),
    ],
)
def test_native_rename_room_invalid(
    map_id: str, room_id: Any, name: str, err: str
) -> None:
    with pytest.raises((ValueError, TypeError), match=err):
        NativeRenameRoom(map_id, room_id, name)
