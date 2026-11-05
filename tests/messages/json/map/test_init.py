from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.commands.json.map import GetMapSetV2
from deebot_client.events import FirmwareEvent
from deebot_client.events.map import (
    CachedMapInfoEvent,
    MajorMapEvent,
    Map,
    MapInfoChunkEvent,
    MapInfoEvent,
    MapSetType,
)
from deebot_client.message import HandlingState
from deebot_client.messages.json import OnMapSetV2
from deebot_client.messages.json.map import OnMajorMap, OnMapInfoV2
from deebot_client.rs.map import RotationAngle
from tests.messages.json import assert_message

if TYPE_CHECKING:
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
        ("2", HandlingState.ANALYSE_LOGGED, False),
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


def _map_info_frame(data: dict[str, object]) -> dict[str, object]:
    return {"header": {"ver": "0.0.1"}, "body": {"data": data}}


def test_onMapInfo_V2_chunk() -> None:
    """Test onMapInfo_V2 chunk without outlineVer."""
    assert_message(
        OnMapInfoV2,
        _map_info_frame(
            {
                "batid": "265357",
                "serial": 2,
                "index": 1,
                "using": 1,
                "mid": "453392179",
                "type": "0",
                "infoSize": 3539,
                "info": "abc",
            }
        ),
        MapInfoChunkEvent("453392179", "265357", 1, 2, "abc"),
    )


@pytest.mark.parametrize(
    ("serial", "index", "expected_state"),
    [
        (0, 0, HandlingState.SUCCESS),
        (2, 2, HandlingState.ANALYSE_LOGGED),
    ],
    ids=["empty", "index_out_of_range"],
)
def test_onMapInfo_V2_chunk_ignored(
    serial: int, index: int, expected_state: HandlingState
) -> None:
    """Test onMapInfo_V2 chunks, which can't be used."""
    assert_message(
        OnMapInfoV2,
        _map_info_frame(
            {
                "batid": "265357",
                "serial": serial,
                "index": index,
                "mid": "453392179",
                "info": "",
            }
        ),
        None,
        expected_state=expected_state,
    )


@pytest.mark.parametrize(
    ("serial", "built"),
    [(2, True), (0, False)],
)
def test_onMapInfo_V2_response_without_info(serial: int, built: bool) -> None:
    """Test getMapInfo_V2 response with only map id and chunk amount."""
    result = assert_message(
        OnMapInfoV2,
        _map_info_frame({"mid": "453392179", "serial": serial}),
        CachedMapInfoEvent(
            {
                Map(
                    id="453392179",
                    name="",
                    using=True,
                    built=built,
                    angle=RotationAngle.DEG_0,
                )
            }
        ),
    )
    assert result.args == {"map_id": "453392179"}


@pytest.mark.parametrize(
    "data",
    [{}, {"mid": "453392179"}, {"mid": "0", "serial": 1}, {"serial": 1}],
    ids=["empty", "no_serial", "map_id_0", "no_map_id"],
)
def test_onMapInfo_V2_unknown_format(data: dict[str, object]) -> None:
    """Test onMapInfo_V2 with an unknown format."""
    assert_message(
        OnMapInfoV2,
        _map_info_frame(data),
        None,
        expected_state=HandlingState.ANALYSE_LOGGED,
    )
