from __future__ import annotations

from typing import Any

import pytest
from testfixtures import LogCapture

from deebot_client.command import CommandResult
from deebot_client.commands.json import (
    GetCachedMapInfo,
    GetMajorMap,
    GetMapSet,
    GetMapSubSet,
    GetMapTrace,
)
from deebot_client.commands.json.map import GetMapSetV2
from deebot_client.events import (
    MajorMapEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MapTraceEvent,
)
from deebot_client.events.map import CachedMapInfoEvent
from deebot_client.message import HandlingState
from tests.helpers import get_request_json, get_success_body

from . import assert_command


@pytest.mark.parametrize(
    ("compress", "value", "expected_coordinates"),
    [
        (
            1,
            "XQAABACZAAAAABaOQmW9Bsibxz42rKUpGlV7Rr4D1S/9x9mDa60v4J1BKrEsnk34EAt6X5gKkxwYzfOu3T8GAPpmIy5o4A==",
            "-9125,3225;-9025,3225;-8975,3175;-8975,2475;-8925,2425;-8925,2375;-8325,2375;-8275,2425;-8225,2375;-8225,2425;-8174,2475;-8024,2475;-8024,4375;-9125,4375",
        ),
        (
            0,
            "1400,1800;1400,3250;3000,3250;3000,2700;2900,2850;2750,2700;2800,1250;2700,1050;2700,850;1450,850;1400,1800",
            "1400,1800;1400,3250;3000,3250;3000,2700;2900,2850;2750,2700;2800,1250;2700,1050;2700,850;1450,850;1400,1800",
        ),
    ],
    ids=["Compressed", "Plain"],
)
@pytest.mark.parametrize(
    ("additional_data", "expected_name"),
    [
        (
            {"subtype": "15", "name": "Levin"},
            "Levin",
        ),
        (
            {"subtype": "1", "name": "Custom"},
            "Custom",
        ),
        (
            {"subtype": "1", "name": ""},
            "Living Room",
        ),
    ],
    ids=["Custom subtype", "Override default name", "Default name"],
)
async def test_getMapSubSet_customName(
    compress: int,
    value: str,
    expected_coordinates: str,
    additional_data: dict[str, Any],
    expected_name: str,
) -> None:
    _type = MapSetType.ROOMS
    mid = "98100521"
    mssid = "8"
    json = get_request_json(
        get_success_body(
            {
                "type": _type.value,
                "connections": "7,",
                "seqIndex": 0,
                "seq": 0,
                "count": 0,
                "totalCount": 50,
                "index": 0,
                "cleanset": "1,0,2",
                "valueSize": 633,
                "compress": compress,
                "center": "-6775,-9225",
                "mssid": mssid,
                "value": value,
                "mid": mid,
                **additional_data,
            }
        )
    )
    await assert_command(
        GetMapSubSet(mid=mid, mssid=mssid, msid="1"),
        json,
        MapSubsetEvent(8, _type, expected_coordinates, expected_name),
    )


@pytest.mark.parametrize(
    ("additional_data", "expected_log_message"),
    [
        ({"subtype": "15"}, "Got room without a name"),
        ({}, "Got room without a name"),
        ({"subType": "bla"}, "Subtype is not a number"),
    ],
    ids=["No custom name", "No subtype", "Subtype not int"],
)
async def test_getMapSubSet_invalid(
    additional_data: dict[str, Any], expected_log_message: str
) -> None:
    mid = "199390082"
    mssid = "1"
    data = {
        "type": MapSetType.ROOMS,
        "mssid": mssid,
        "value": "-442,2910;-442,982;1214,982;1214,2910",
        "connections": "12",
        "mid": mid,
        **additional_data,
    }
    json = get_request_json(get_success_body(data))
    with LogCapture() as log:
        await assert_command(
            GetMapSubSet(mid=mid, mssid=mssid, msid="1"),
            json,
            None,
            command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
        )

        log.check_present(
            (
                "deebot_client.commands.json.map",
                "WARNING",
                expected_log_message,
            )
        )
        log.check_present(
            (
                "deebot_client.message",
                "DEBUG",
                f"Could not handle getMapSubSet message: {data}",
            )
        )


def _getMapSubSet_room_valid_response(value: str, id: int) -> dict[str, Any]:
    return get_request_json(
        get_success_body(
            {
                "type": MapSetType.ROOMS.value,
                "mssid": str(id),
                "value": value,
                "subtype": "1",
                "connections": "12",
                "mid": "199390082",
            }
        )
    )


async def test_getMapSubSet_living_room() -> None:
    value = "-1400,-1600;-1400,-1350;-950,-1100;-900,-150;-550,100;200,950;500,950;650,800;800,950;1850,950;1950,800;1950,-200;2050,-300;2300,-300;2550,-650;2700,-650;2700,-1600;2400,-1750;2700,-1900;2700,-2950;2450,-2950;2300,-3100;2400,-3200;2650,-3200;2700,-3500;2300,-3500;2200,-3250;2050,-3550;1200,-3550;1200,-3300;1050,-3200;950,-3300;950,-3550;600,-3550;550,-2850;850,-2800;950,-2700;850,-2600;950,-2400;900,-2350;800,-2300;550,-2500;550,-2350;400,-2250;200,-2650;-800,-2650;-950,-2550;-950,-2150;-650,-2000;-450,-2000;-400,-1950;-450,-1850;-750,-1800;-950,-1900;-1350,-1900;-1400,-1600"
    json = _getMapSubSet_room_valid_response(value, 7)
    await assert_command(
        GetMapSubSet(mid="199390082", mssid="7", msid="1"),
        json,
        MapSubsetEvent(7, MapSetType.ROOMS, value, "Living Room"),
    )


@pytest.mark.parametrize(
    ("command", "map_set_type"),
    [
        (GetCachedMapInfo(), GetMapSet),
        (GetCachedMapInfo(version=1), GetMapSet),
        (GetCachedMapInfo(version=2), GetMapSetV2),
    ],
)
async def test_getCachedMapInfo(
    command: GetCachedMapInfo, map_set_type: type[GetMapSet | GetMapSetV2]
) -> None:
    expected_mid = "199390082"
    expected_name = "Erdgeschoss"
    json = get_request_json(
        get_success_body(
            {
                "enable": 1,
                "info": [
                    {
                        "mid": expected_mid,
                        "index": 0,
                        "status": 1,
                        "using": 1,
                        "built": 1,
                        "name": expected_name,
                    },
                    {
                        "mid": "722607162",
                        "index": 3,
                        "status": 0,
                        "using": 0,
                        "built": 0,
                        "name": "",
                    },
                ],
            }
        )
    )
    await assert_command(
        command,
        json,
        CachedMapInfoEvent(expected_name, active=True),
        command_result=CommandResult(
            HandlingState.SUCCESS,
            {"map_id": expected_mid},
            [map_set_type(expected_mid, entry) for entry in MapSetType],
        ),
    )


async def test_getMajorMap() -> None:
    expected_mid = "199390082"
    value = "1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,3378526980,2963288214,2739565817,729228561,2452519304,1295764014,1295764014,1295764014,2753376360,329080101,952462272,3648890579,412193448,1540631558,1295764014,1295764014,1561391782,1081327924,1096350476,2860639280,37066625,86907282,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014"
    json = get_request_json(
        get_success_body(
            {
                "mid": expected_mid,
                "pieceWidth": 100,
                "pieceHeight": 100,
                "cellWidth": 8,
                "cellHeight": 8,
                "pixel": 50,
                "value": value,
            }
        )
    )
    await assert_command(
        GetMajorMap(),
        json,
        MajorMapEvent(expected_mid, value.split(","), requested=True),
    )


async def test_getMapSet() -> None:
    mid = "199390082"
    msid = "8"
    room_value = "-442,2910;-442,982;1214,982;1214,2910"
    subsets = [7, 12, 17, 14, 10, 11, 13]
    json = (
        # getMapSet response
        get_request_json(
            get_success_body(
                {
                    "type": "ar",
                    "count": 7,
                    "mid": mid,
                    "msid": msid,
                    "subsets": [
                        {"mssid": "7"},
                        {"mssid": "12"},
                        {"mssid": "17"},
                        {"mssid": "14"},
                        {"mssid": "10"},
                        {"mssid": "11"},
                        {"mssid": "13"},
                    ],
                }
            )
        ),
        # getMapSubSet response
        *(_getMapSubSet_room_valid_response(room_value, subset) for subset in subsets),
    )
    await assert_command(
        GetMapSet(mid),
        json,
        (
            MapSetEvent(MapSetType.ROOMS, subsets),
            *(
                MapSubsetEvent(subset, MapSetType.ROOMS, room_value, "Living Room")
                for subset in subsets
            ),
        ),
        command_result=CommandResult(
            HandlingState.SUCCESS,
            {"id": mid, "set_id": msid, "type": MapSetType.ROOMS, "subsets": subsets},
            [
                GetMapSubSet(mid=mid, msid=msid, type=MapSetType.ROOMS, mssid=s)
                for s in subsets
            ],
        ),
    )


async def test_getMapSetV2_no_mop_zones() -> None:
    mid = "199390082"
    type = MapSetType.NO_MOP_ZONES
    json = get_request_json(
        get_success_body(
            {
                "type": type,
                "mid": mid,
                "batid": "fbfebf",
                "serial": 1,
                "index": 1,
                "subsets": "XQAABABBAAAAAC2WwEIwUhHX3vfFDfs1H1PUqtdWgakwVnMBz3Bb3yaoE5OYkdYA",
                "infoSize": 65,
            }
        )
    )
    await assert_command(
        GetMapSetV2(mid, type),
        json,
        (
            MapSubsetEvent(
                4,
                type,
                str(["-6217", "3919", "-6217", "231", "-2642", "231", "-2642", "3919"]),
            ),
        ),
    )


async def test_getMapSetV2_rooms() -> None:
    mid = "199390082"
    msid = "8"
    type = MapSetType.ROOMS
    subsets_comp = (
        "XQAABADnAQAAAC2WwEHwYhHYFuLu9964T0CAIjkOBSGKBW+PcTQDCjKFThR86eaw4bFiV2BKLAP+0lTYd1ADOkmjNPrfSqBeHZLY4JNCaEMc2H245BSG143miuQm6X6"
        "KeTCnXV7Er028XLcnN9q/immzxeoPpkdhnbhuL9f8jW5kgVLGPJnfv2V2a79W4PjkSR4b4Px632ID+UKVwGL1mYiwNnMO35XA41W+pPsgW12ZRnsMDvGMAlv4VLhDJFAy4AA="
    )
    subsets = [0, 1, 6, 2, 7, 3, 5]
    room_value = "-442,2910;-442,982;1214,982;1214,2910"
    json = (
        # GetMapSetV2 response
        get_request_json(
            get_success_body(
                {
                    "type": type,
                    "mid": mid,
                    "msid": msid,
                    "batid": "gheijg",
                    "serial": 1,
                    "index": 1,
                    "subsets": subsets_comp,
                    "infoSize": 199,
                }
            )
        ),
        # getMapSubSet response
        *(_getMapSubSet_room_valid_response(room_value, subset) for subset in subsets),
    )

    await assert_command(
        GetMapSetV2(mid, type),
        json,
        (
            MapSetEvent(MapSetType(type), subsets),
            *(
                MapSubsetEvent(subset, MapSetType.ROOMS, room_value, "Living Room")
                for subset in subsets
            ),
        ),
        command_result=CommandResult(
            HandlingState.SUCCESS,
            {"id": mid, "set_id": msid, "type": MapSetType(type), "subsets": subsets},
            [GetMapSubSet(mid=mid, msid=msid, type=type, mssid=s) for s in subsets],
        ),
    )


async def test_getMapSetV2_virtual_walls() -> None:
    mid = "199390082"
    type = MapSetType.VIRTUAL_WALLS
    json = get_request_json(
        get_success_body(
            {
                "type": type,
                "mid": mid,
                "batid": "gheijg",
                "serial": 1,
                "index": 1,
                "subsets": "XQAABADHAAAAAC2WwEHwYhHX3vWwDK80QCnaQU0mwUd9Vk34ub6OxzOk6kdFfbFvpVp4iIlKisAvp0MznQNYEZ8koxFHnO,+iM44GUKgujGQKgzl0bScbQgaon1jI3eyCRikWlkmrbwA=",
                "infoSize": 199,
            }
        )
    )

    expected_walls: list[dict[str, str | int]] = [
        {
            "mssid": 0,
            "coordinates": str(
                ["-5195", "-1059", "-5195", "-37", "-5806", "-37", "-5806", "-1059"]
            ),
        },
        {
            "mssid": 1,
            "coordinates": str(
                ["-7959", "220", "-7959", "1083", "-9254", "1083", "-9254", "220"]
            ),
        },
        {"mssid": 2, "coordinates": str(["-9437", "347", "-5387", "410"])},
        {"mssid": 3, "coordinates": str(["-5667", "317", "-4888", "-56"])},
    ]

    await assert_command(
        GetMapSetV2(mid, type),
        json,
        [
            MapSubsetEvent(int(subs["mssid"]), type, str(subs["coordinates"]))
            for subs in expected_walls
        ],
    )


async def test_getMapTrace() -> None:
    start = 0
    total = 160
    trace_value = "REMOVED"
    json = get_request_json(
        get_success_body(
            {
                "tid": "173207",
                "totalCount": total,
                "traceStart": start,
                "pointCount": 200,
                "traceValue": trace_value,
            }
        )
    )
    await assert_command(
        GetMapTrace(start),
        json,
        MapTraceEvent(start=start, total=total, data=trace_value),
        command_result=CommandResult(
            HandlingState.SUCCESS, {"start": start, "total": total}, []
        ),
    )
