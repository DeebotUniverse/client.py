from __future__ import annotations

import pytest

from deebot_client.commands.json.map import GetMapSetV2
from deebot_client.events import FirmwareEvent
from deebot_client.events.map import MajorMapEvent, MapSetType
from deebot_client.messages.json import OnMapSetV2
from deebot_client.messages.json.map import OnMajorMap
from tests.messages.json import assert_message


@pytest.mark.parametrize(
    ("mid", "set_type"),
    [
        ("199390082", MapSetType.ROOMS),
        ("199390082", MapSetType.NO_MOP_ZONES),
        ("199390082", MapSetType.VIRTUAL_WALLS),
    ],
)
async def test_onMapSetV2(mid: str, set_type: MapSetType) -> None:
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

    result = await assert_message(
        OnMapSetV2,
        data,
        (FirmwareEvent("1.8.2"),),
    )
    assert result.requested_commands == [GetMapSetV2(mid, set_type)]


async def test_onMajorMap() -> None:
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

    result = await assert_message(
        OnMajorMap,
        data,
        (FirmwareEvent("1.34.0"), MajorMapEvent(map_id, values, requested=False)),
    )
    assert result.args == {"map_id": map_id, "values": values}
