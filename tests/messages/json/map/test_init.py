from __future__ import annotations

from base64 import b64encode
from compression.zstd import compress
from typing import TYPE_CHECKING

from defusedxml.ElementTree import fromstring
import orjson
import pytest

from deebot_client.commands.json.map import GetMapInfoV2, GetMapSetV2
from deebot_client.events import FirmwareEvent
from deebot_client.events.map import MajorMapEvent, MapInfoEvent, MapSetType
from deebot_client.message import HandlingState
from deebot_client.messages.json import OnMapSetV2
from deebot_client.messages.json.map import OnMajorMap, OnMapInfoV2
from deebot_client.rs.map import MapData, RotationAngle
from tests.helpers import get_request_json, get_success_body
from tests.messages.json import assert_message

if TYPE_CHECKING:
    from unittest.mock import Mock

    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    ("mid", "set_type"),
    [
        ("199390082", MapSetType.ROOMS),
        ("199390082", MapSetType.NO_MOP_ZONES),
        ("199390082", MapSetType.VIRTUAL_WALLS),
    ],
)
@pytest.mark.benchmark
def test_onMapSetV2(mid: str, set_type: MapSetType) -> None:
    data = {
        "header": {
            "pri": 1,
            "tzm": 480,
            "ts": "1304637391896",
            "ver": "0.0.1",
            "fwVer": "1.8.2",
            "hwVer": "0.1.1",
        },
        "body": {"data": {"mid": mid, "type": set_type.value}},
    }

    result = assert_message(
        OnMapSetV2,
        data,
        (FirmwareEvent("1.8.2"),),
    )
    assert result.requested_commands == [GetMapSetV2(mid, set_type)]


@pytest.mark.benchmark
def test_onMajorMap() -> None:
    """Test onMajorMap message."""
    map_id = "1132127808"
    values = [
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        817288174,
        3571566673,
        2120918229,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        4119863044,
        3345372489,
        1125149782,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        2826859129,
        3628293953,
        1436915986,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        3857336909,
        2692517274,
        3424129059,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        1295764014,
        2514771601,
        2675258590,
        3347634930,
        1295764014,
        1295764014,
        1295764014,
    ]
    data = {
        "header": {
            "pri": 1,
            "tzm": 60,
            "ts": "1758910287614",
            "ver": "0.0.1",
            "fwVer": "1.34.0",
            "hwVer": "0.1.1",
            "wkVer": "0.1.54",
        },
        "body": {
            "data": {
                "mid": map_id,
                "pieceWidth": 100,
                "pieceHeight": 100,
                "cellWidth": 8,
                "cellHeight": 8,
                "pixel": 50,
                "value": ",".join(map(str, values)),
                "type": "ol",
            }
        },
    }

    result = assert_message(
        OnMajorMap,
        data,
        (FirmwareEvent("1.34.0"), MajorMapEvent(map_id, values, requested=False)),
    )
    assert result.args == {"map_id": map_id, "values": values}


@pytest.mark.parametrize(
    ("online_ver", "expected_state", "should_notify"),
    [
        ("0", HandlingState.SUCCESS, False),
        ("1", HandlingState.SUCCESS, True),
        ("2", HandlingState.SUCCESS, True),
        ("3", HandlingState.ANALYSE_LOGGED, False),
    ],
)
@pytest.mark.benchmark
def test_onMapInfo_V2(
    online_ver: str,
    expected_state: HandlingState,
    should_notify: bool,
) -> None:
    """Test onMapInfo_V2 message with unsupported version."""
    map_id = "1132127808"
    info = "KLUv/WBuAOUEAMKHEhGgJc0B/t+e/8tOpCUXnv6wB8MgkzOv8aaVcx83Ob970V2jqKjyDrpZulk0ORMwrriigTNeNNYSRZhBAHQ196KaaTODukBGSgQhJSCAojXXDSMFoBmkm5nkvB5Fd1Y/Egyq8WAN/OJ0DezknG5gqwa6MBfBRW+sfLOsgLwKK4gZv4feNsH2ufM7AGNqAo/2u6QQXgAi1EMPAw=="
    data = {
        "header": {
            "pri": 1,
            "tzm": 60,
            "ts": "1758910287614",
            "ver": "0.0.1",
            "fwVer": "1.34.0",
            "hwVer": "0.1.1",
            "wkVer": "0.1.54",
        },
        "body": {
            "data": {
                "batid": "ampigk",
                "index": "1",
                "info": info,
                "infoSize": 366,
                "mid": map_id,
                "msgid": "",
                "outlineComplete": 0,
                "outlineVer": online_ver,
                "serial": "1",
                "type": "0",
                "using": 0,
            }
        },
    }

    expected_events: list[Event] = [FirmwareEvent("1.34.0")]
    if should_notify:
        expected_events.append(MapInfoEvent(map_id, info))

    assert_message(
        OnMapInfoV2,
        data,
        expected_events,
        expected_state=expected_state,
    )


@pytest.mark.parametrize("message", [OnMapInfoV2, GetMapInfoV2])
def test_map_info_v2_renders_outline_version_2(
    message: type[OnMapInfoV2], event_bus_mock: Mock
) -> None:
    """Render synthetic V2 outline, room and block-line layers without map tiles."""
    layers = [
        ["1", "1;0,0,1;200,0,1;200,100,1;0,100,1"],
        ["2", "1;0,0;200,0;200,100;0,100"],
        ["6", "1;0,0;200,0;200,100;0,100"],
    ]
    info = b64encode(compress(orjson.dumps(layers))).decode()
    payload, _ = get_request_json(
        get_success_body({"mid": "1", "outlineVer": "2", "info": info})
    )

    result = message.handle(event_bus_mock, payload["resp"])

    assert result.state is HandlingState.SUCCESS
    map_events = [
        call.args[0]
        for call in event_bus_mock.notify.call_args_list
        if isinstance(call.args[0], MapInfoEvent)
    ]
    assert map_events == [MapInfoEvent("1", info)]
    map_data = MapData()
    map_data.map_info.set(map_events[0].info)
    svg = map_data.generate_svg([], [], RotationAngle.DEG_0)

    assert svg is not None
    root = fromstring(svg)
    # The renderer uses 50 mm per SVG unit and inverts the Y axis.
    assert root.attrib["viewBox"] == "0 -2 4 2"
    assert (
        len(root.findall("svg:g/svg:path", {"svg": "http://www.w3.org/2000/svg"})) == 4
    )
