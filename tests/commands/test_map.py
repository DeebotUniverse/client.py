from deebot_client.commands import (
    GetCachedMapInfo,
    GetMajorMap,
    GetMapSet,
    GetMapSubSet,
    GetMapTrace,
)
from deebot_client.commands.common import CommandResult
from deebot_client.events import (
    MajorMapEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MapTraceEvent,
)
from deebot_client.message import HandlingState
from tests.commands import assert_command_requested
from tests.helpers import get_request_json


def test_getMapSubSet_requested_customName() -> None:
    type = MapSetType.ROOMS
    value = "XQAABAB5AgAAABaOQok5MfkIKbGTBxaUTX13SjXBAI1/Q3A9Kkx2gYZ1QdgwfwOSlU3hbRjNJYgr2Pr3WgFez3Gcoj3R2JmzAuc436F885ZKt5NF2AE1UPAF4qq67tK6TSA64PPfmZQ0lqwInQmqKG5/KO59RyFBbV1NKnDIGNBGVCWpH62WLlMu8N4zotA8dYMQ/UBMwr/gddQO5HU01OQM2YvF"
    name = "Levin"
    json = get_request_json(
        {
            "type": type.value,
            "subtype": "15",
            "connections": "7,",
            "name": name,
            "seqIndex": 0,
            "seq": 0,
            "count": 0,
            "totalCount": 50,
            "index": 0,
            "cleanset": "1,0,2",
            "valueSize": 633,
            "compress": 1,
            "center": "-6775,-9225",
            "mssid": "8",
            "value": value,
            "mid": "98100521",
        }
    )
    assert_command_requested(
        GetMapSubSet(mid="98100521", mssid="8", msid="1"),
        json,
        MapSubsetEvent(8, type, value, name),
    )


def test_getMapSubSet_requested_living_room() -> None:
    type = MapSetType.ROOMS
    value = "-1400,-1600;-1400,-1350;-950,-1100;-900,-150;-550,100;200,950;500,950;650,800;800,950;1850,950;1950,800;1950,-200;2050,-300;2300,-300;2550,-650;2700,-650;2700,-1600;2400,-1750;2700,-1900;2700,-2950;2450,-2950;2300,-3100;2400,-3200;2650,-3200;2700,-3500;2300,-3500;2200,-3250;2050,-3550;1200,-3550;1200,-3300;1050,-3200;950,-3300;950,-3550;600,-3550;550,-2850;850,-2800;950,-2700;850,-2600;950,-2400;900,-2350;800,-2300;550,-2500;550,-2350;400,-2250;200,-2650;-800,-2650;-950,-2550;-950,-2150;-650,-2000;-450,-2000;-400,-1950;-450,-1850;-750,-1800;-950,-1900;-1350,-1900;-1400,-1600"
    json = get_request_json(
        {
            "type": type.value,
            "mssid": "7",
            "value": value,
            "subtype": "1",
            "connections": "12",
            "mid": "199390082",
        }
    )
    assert_command_requested(
        GetMapSubSet(mid="199390082", mssid="7", msid="1"),
        json,
        MapSubsetEvent(7, type, value, "Living Room"),
    )


def test_getCachedMapInfo_requested() -> None:
    expected_mid = "199390082"
    json = get_request_json(
        {
            "enable": 1,
            "info": [
                {
                    "mid": expected_mid,
                    "index": 0,
                    "status": 1,
                    "using": 1,
                    "built": 1,
                    "name": "Erdgeschoss",
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
    assert_command_requested(
        GetCachedMapInfo(),
        json,
        None,
        CommandResult(
            HandlingState.SUCCESS,
            {"map_id": expected_mid},
            [GetMapSet(expected_mid, entry) for entry in MapSetType],
        ),
    )


def test_getMajorMap_requested() -> None:
    expected_mid = "199390082"
    value = "1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,3378526980,2963288214,2739565817,729228561,2452519304,1295764014,1295764014,1295764014,2753376360,329080101,952462272,3648890579,412193448,1540631558,1295764014,1295764014,1561391782,1081327924,1096350476,2860639280,37066625,86907282,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014"
    json = get_request_json(
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
    assert_command_requested(
        GetMajorMap(), json, MajorMapEvent(True, expected_mid, value.split(","))
    )


def test_getMapSet_requested() -> None:
    mid = "199390082"
    msid = "8"
    json = get_request_json(
        {
            "type": "ar",
            "count": 7,
            "mid": mid,
            "msid": "8",
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
    subsets = [7, 12, 17, 14, 10, 11, 13]
    assert_command_requested(
        GetMapSet(mid),
        json,
        MapSetEvent(MapSetType.ROOMS, subsets),
        CommandResult(
            HandlingState.SUCCESS,
            {"id": "199390082", "set_id": "8", "type": "ar", "subsets": subsets},
            [
                GetMapSubSet(mid=mid, msid=msid, type=MapSetType.ROOMS, mssid=s)
                for s in subsets
            ],
        ),
    )


def test_getMapTrace_requested() -> None:
    start = 0
    total = 2545
    trace_value = "REMOVED"
    json = get_request_json(
        {
            "tid": "173207",
            "totalCount": 2545,
            "traceStart": start,
            "pointCount": 200,
            "traceValue": trace_value,
        }
    )
    assert_command_requested(
        GetMapTrace(start),
        json,
        MapTraceEvent(start=start, total=total, data=trace_value),
        CommandResult(
            HandlingState.SUCCESS, {"start": start, "total": total}, [GetMapTrace(200)]
        ),
    )
