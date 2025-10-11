from __future__ import annotations

from typing import Any

import pytest
from testfixtures import LogCapture

from deebot_client.commands.json import (
    GetMapSet,
    GetMapSubSet,
    GetMapTrace,
)
from deebot_client.commands.json.map import GetMapSetV2
from deebot_client.events import (
    Event,
    FirmwareEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MapTraceEvent,
    RoomsEvent,
)
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import Room
from tests.commands.json import assert_command
from tests.helpers import get_request_json, get_success_body


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
    json, firmware_event = get_request_json(
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
        [firmware_event, MapSubsetEvent(8, _type, expected_coordinates, expected_name)],
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
    json, firmware_event = get_request_json(get_success_body(data))
    with LogCapture() as log:
        await assert_command(
            GetMapSubSet(mid=mid, mssid=mssid, msid="1"),
            json,
            firmware_event,
            handling_result=HandlingResult(HandlingState.ANALYSE_LOGGED),
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


def _getMapSubSet_room_valid_response(
    value: str, map_id: int
) -> tuple[dict[str, Any], FirmwareEvent]:
    return get_request_json(
        get_success_body(
            {
                "type": MapSetType.ROOMS.value,
                "mssid": str(map_id),
                "value": value,
                "subtype": "1",
                "connections": "12",
                "mid": "199390082",
            }
        )
    )


async def test_getMapSubSet_living_room() -> None:
    value = "-1400,-1600;-1400,-1350;-950,-1100;-900,-150;-550,100;200,950;500,950;650,800;800,950;1850,950;1950,800;1950,-200;2050,-300;2300,-300;2550,-650;2700,-650;2700,-1600;2400,-1750;2700,-1900;2700,-2950;2450,-2950;2300,-3100;2400,-3200;2650,-3200;2700,-3500;2300,-3500;2200,-3250;2050,-3550;1200,-3550;1200,-3300;1050,-3200;950,-3300;950,-3550;600,-3550;550,-2850;850,-2800;950,-2700;850,-2600;950,-2400;900,-2350;800,-2300;550,-2500;550,-2350;400,-2250;200,-2650;-800,-2650;-950,-2550;-950,-2150;-650,-2000;-450,-2000;-400,-1950;-450,-1850;-750,-1800;-950,-1900;-1350,-1900;-1400,-1600"
    json, firmware_event = _getMapSubSet_room_valid_response(value, 7)
    await assert_command(
        GetMapSubSet(mid="199390082", mssid="7", msid="1"),
        json,
        [firmware_event, MapSubsetEvent(7, MapSetType.ROOMS, value, "Living Room")],
    )


async def test_getMapSet() -> None:
    mid = "199390082"
    msid = "8"
    room_value = "-442,2910;-442,982;1214,982;1214,2910"
    subsets = [7, 12, 17, 14, 10, 11, 13]
    data, firmware_event = get_request_json(
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
    )
    json = (
        # getMapSet response
        data,
        # getMapSubSet response
        *(
            _getMapSubSet_room_valid_response(room_value, subset)[0]
            for subset in subsets
        ),
    )
    events = [firmware_event, MapSetEvent(MapSetType.ROOMS, subsets)]
    for subset in subsets:
        events.extend(
            [
                firmware_event,
                MapSubsetEvent(subset, MapSetType.ROOMS, room_value, "Living Room"),
            ]
        )
    await assert_command(
        GetMapSet(mid),
        json,
        events,
        handling_result=HandlingResult(
            HandlingState.SUCCESS,
            {"id": mid, "set_id": msid, "type": MapSetType.ROOMS, "subsets": subsets},
            [
                GetMapSubSet(mid=mid, msid=msid, type=MapSetType.ROOMS, mssid=s)
                for s in subsets
            ],
        ),
    )


@pytest.mark.parametrize(
    ("map_id", "set_type", "response_data", "expected_events"),
    [
        (
            "1132127808",
            MapSetType.VIRTUAL_WALLS,
            {
                "type": "vw",
                "mid": "1132127808",
                "batid": "lohgbd",
                "serial": 1,
                "index": 1,
                "subsets": "XQAABABKAAAAAC2WwEHwYhHX6tw2FeZC6xrq6vMnCbIHn24XWkCfMo5aBq/u/ucF6zdYzFkR6WdJiSWdWFww2d2gAA==",
                "infoSize": 74,
            },
            [
                MapSubsetEvent(
                    0,
                    MapSetType.VIRTUAL_WALLS,
                    "['12023', '1979', '12135', '-6720']",
                ),
                MapSubsetEvent(
                    1,
                    MapSetType.VIRTUAL_WALLS,
                    "['2120', '-4581', '2106', '-6271']",
                ),
                MapSetEvent(MapSetType.VIRTUAL_WALLS, [0, 1]),
            ],
        ),
        (
            "199390082",
            MapSetType.NO_MOP_ZONES,
            {
                "type": "mw",
                "mid": "199390082",
                "batid": "fbfebf",
                "serial": 1,
                "index": 1,
                "subsets": "XQAABABBAAAAAC2WwEIwUhHX3vfFDfs1H1PUqtdWgakwVnMBz3Bb3yaoE5OYkdYA",
                "infoSize": 65,
            },
            [
                MapSubsetEvent(
                    4,
                    MapSetType.NO_MOP_ZONES,
                    "['-6217', '3919', '-6217', '231', '-2642', '231', '-2642', '3919']",
                ),
                MapSetEvent(MapSetType.NO_MOP_ZONES, [4]),
            ],
        ),
        (
            "199390082",
            MapSetType.VIRTUAL_WALLS,
            {
                "type": "vw",
                "mid": "199390082",
                "batid": "fbfebf",
                "serial": 1,
                "index": 1,
                "subsets": "XQAABADHAAAAAC2WwEHwYhHX3vWwDK80QCnaQU0mwUd9Vk34ub6OxzOk6kdFfbFvpVp4iIlKisAvp0MznQNYEZ8koxFHnO+iM44GUKgujGQKgzl0bScbQgaon1jI3eyCRikWlkmrbwA=",
                "infoSize": 199,
            },
            [
                MapSubsetEvent(
                    0,
                    MapSetType.VIRTUAL_WALLS,
                    "['-5195', '-1059', '-5195', '-37', '-5806', '-37', '-5806', '-1059']",
                ),
                MapSubsetEvent(
                    1,
                    MapSetType.VIRTUAL_WALLS,
                    "['-7959', '220', '-7959', '1083', '-9254', '1083', '-9254', '220']",
                ),
                MapSubsetEvent(
                    2,
                    MapSetType.VIRTUAL_WALLS,
                    "['-9437', '347', '-5387', '410']",
                ),
                MapSubsetEvent(
                    3,
                    MapSetType.VIRTUAL_WALLS,
                    "['-5667', '317', '-4888', '-56']",
                ),
                MapSetEvent(MapSetType.VIRTUAL_WALLS, [0, 1, 2, 3]),
            ],
        ),
        (
            "199390082",
            MapSetType.VIRTUAL_WALLS,
            {
                "type": "vw",
                "mid": "199390082",
                "batid": "fbfebf",
                "serial": 1,
                "index": 1,
                "subsets": "KLUv/SBvBQIAIoQLD7ClOUgeYW23kLUHq0+mKqXciplXrVfzUtWcCMuwoGY+xF3QANDcaNjMaR4mJAUAMVIPfD2qwcr0iTHmGA==",
                "infoSize": 111,
            },
            [
                MapSubsetEvent(
                    0,
                    MapSetType.VIRTUAL_WALLS,
                    "['-4814', '12059', '-4814', '7768', '-3948', '7768', '-3948', '12059']",
                ),
                MapSubsetEvent(
                    1,
                    MapSetType.VIRTUAL_WALLS,
                    "['3315', '3754', '3353', '-655']",
                ),
                MapSetEvent(MapSetType.VIRTUAL_WALLS, [0, 1]),
            ],
        ),
    ],
)
async def test_getMapSetV2(
    map_id: str,
    set_type: MapSetType,
    response_data: dict[str, Any],
    expected_events: list[Event],
) -> None:
    json, firmware_event = get_request_json(get_success_body(response_data))
    await assert_command(
        GetMapSetV2(map_id, set_type),
        json,
        (firmware_event, *expected_events),
    )


async def test_getMapSetV2_rooms() -> None:
    mid = "199390082"
    msid = "8"
    set_type = MapSetType.ROOMS
    subsets_comp = (
        "XQAABADnAQAAAC2WwEHwYhHYFuLu9964T0CAIjkOBSGKBW+PcTQDCjKFThR86eaw4bFiV2BKLAP+0lTYd1ADOkmjNPrfSqBeHZLY4JNCaEMc2H245BSG143miuQm6X6"
        "KeTCnXV7Er028XLcnN9q/immzxeoPpkdhnbhuL9f8jW5kgVLGPJnfv2V2a79W4PjkSR4b4Px632ID+UKVwGL1mYiwNnMO35XA41W+pPsgW12ZRnsMDvGMAlv4VLhDJFAy4AA="
    )
    subsets = [0, 1, 6, 2, 7, 3, 5]
    room_value = "-442,2910;-442,982;1214,982;1214,2910"
    data, firmware_event = get_request_json(
        get_success_body(
            {
                "type": set_type,
                "mid": mid,
                "msid": msid,
                "batid": "gheijg",
                "serial": 1,
                "index": 1,
                "subsets": subsets_comp,
                "infoSize": 199,
            }
        )
    )
    json = (
        # GetMapSetV2 response
        data,
        # getMapSubSet response
        *(
            _getMapSubSet_room_valid_response(room_value, subset)[0]
            for subset in subsets
        ),
    )
    events = [firmware_event, MapSetEvent(MapSetType(set_type), subsets)]
    for subset in subsets:
        events.extend(
            [
                firmware_event,
                MapSubsetEvent(subset, set_type, room_value, "Living Room"),
            ]
        )

    await assert_command(
        GetMapSetV2(mid, set_type),
        json,
        events,
        handling_result=HandlingResult(
            HandlingState.SUCCESS,
            {
                "id": mid,
                "set_id": msid,
                "type": MapSetType(set_type),
                "subsets": subsets,
            },
            [GetMapSubSet(mid=mid, msid=msid, type=set_type, mssid=s) for s in subsets],
        ),
    )


async def test_getMapSetV2_rooms_v2() -> None:
    mid = "199390082"
    msid = "8"
    set_type = MapSetType.ROOMS
    subsets_comp = "KLUv/QRYbQkA8k4qH1BJnTEAUTcKhN4AyDMuGmoj/HEQiYgQ8Tz4yG5mdkJJsr5jx1WuQkxjIDkC442Nv0S0QJNiGGeOqSoJwUwA40sP1TTGtTiAnATHML658MQySQTjqmwpXUtzNVVTab502ZKNr44/jxIwbuzBlO17LrVYHqcpjDuVu9rW2Mw1vhamrVNrQA4bwWQdL8Y3VWprz9gcV+Nt3I0jHA5RIykFRcRICGVgfI0gATYggCIJ5rYDyrgQ2IomYhArc8MsZlS2h4UkRLyQBcUnRmAZTEFcfstWEWcbJCwSpBjBzvzPGP5DAEjA0k2iE+AxD3Bv6LfYgkwegjGBoLirkL3BIIZ0VhEAAhR4Dl5A0Aa/0i9ohzgSX3JAyoGMiCe8rhUTxUjGirE9chY0oQmhDLNFpRg="
    subsets = [3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15]
    rooms_names = [
        "Master bathroom",
        "Main bathroom",
        "Master bedroom",
        "Child 1",
        "Child 2",
        "Hall",
        "Child 3",
        "Study",
        "Living room",
        "Guest bathroom",
        "Laundry room",
        "Kitchen",
    ]
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "type": set_type,
                "mid": mid,
                "msid": msid,
                "batid": "gheijg",
                "serial": 1,
                "index": 1,
                "subsets": subsets_comp,
                "infoSize": 780,
            }
        )
    )
    rooms = [
        Room(room_name, subset, "")
        for subset, room_name in zip(subsets, rooms_names, strict=False)
    ]
    events = [firmware_event, RoomsEvent(rooms)]

    await assert_command(
        GetMapSetV2(mid, set_type),
        json,
        events,
    )


async def test_getMapTrace() -> None:
    start = 0
    total = 160
    trace_value = "REMOVED"
    (
        json,
        firmware_event,
    ) = get_request_json(
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
        (firmware_event, MapTraceEvent(start=start, total=total, data=trace_value)),
        handling_result=HandlingResult(
            HandlingState.SUCCESS, {"start": start, "total": total}, []
        ),
    )
