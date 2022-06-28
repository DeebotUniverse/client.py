from deebot_client.commands import GetMapSubSet
from deebot_client.events import MapSetType, MapSubsetEvent
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
