from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json import (
    GetMajorMap,
)
from deebot_client.commands.json.map.major_map import SetMajorMap
from deebot_client.events import (
    MajorMapEvent,
)
from deebot_client.message import HandlingResult, HandlingState
from tests.commands.json import assert_command, assert_set_command
from tests.helpers import get_request_json, get_success_body


@pytest.mark.parametrize(
    ("request_data", "expected"),
    [
        (
            {
                "mid": "199390082",
                "pieceWidth": 100,
                "pieceHeight": 100,
                "cellWidth": 8,
                "cellHeight": 8,
                "pixel": 50,
                "value": "1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,3378526980,2963288214,2739565817,729228561,2452519304,1295764014,1295764014,1295764014,2753376360,329080101,952462272,3648890579,412193448,1540631558,1295764014,1295764014,1561391782,1081327924,1096350476,2860639280,37066625,86907282,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014,1295764014",
            },
            MajorMapEvent(
                "199390082",
                [
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
                    3378526980,
                    2963288214,
                    2739565817,
                    729228561,
                    2452519304,
                    1295764014,
                    1295764014,
                    1295764014,
                    2753376360,
                    329080101,
                    952462272,
                    3648890579,
                    412193448,
                    1540631558,
                    1295764014,
                    1295764014,
                    1561391782,
                    1081327924,
                    1096350476,
                    2860639280,
                    37066625,
                    86907282,
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
                ],
                requested=True,
            ),
        ),
        (
            {
                "cellHeight": 1,
                "cellWidth": 1,
                "mid": "2035288016",
                "pieceHeight": 800,
                "pieceWidth": 800,
                "pixel": 50,
                "type": "ol",
                "value": "",
            },
            MajorMapEvent("2035288016", [], requested=True),
        ),
    ],
)
async def test_getMajorMap(
    request_data: dict[str, Any], expected: MajorMapEvent
) -> None:
    json, firmware_event = get_request_json(get_success_body(request_data))

    await assert_command(
        GetMajorMap(),
        json,
        [
            firmware_event,
            MajorMapEvent(expected.map_id, expected.values, requested=False),
            expected,
        ],
        handling_result=HandlingResult(
            HandlingState.SUCCESS,
            args={"map_id": expected.map_id, "values": expected.values},
        ),
    )


async def test_SetMajorMap() -> None:
    """Test setting the major map (selecting a map)."""
    map_id = "199390082"
    args = {"mid": map_id}
    await assert_set_command(
        SetMajorMap(map_id), args, MajorMapEvent(map_id, [], requested=False)
    )
