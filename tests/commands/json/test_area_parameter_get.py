from __future__ import annotations

from deebot_client.commands.json import GetAreaParameter
from deebot_client.events import AreaParameter, AreaParameterEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command


async def test_GetAreaParameter() -> None:
    json, firmware_event = get_request_json(
        get_success_body(
            {
                "areaParameters": [
                    {
                        "areaID": "2",
                        "mowHeightLevel": 10,
                        "cutMode": 7,
                        "obstacleHeight": 1,
                        "angle": 180,
                    },
                    {
                        "areaID": "3",
                        "mowHeightLevel": 9,
                        "cutMode": 4,
                        "obstacleHeight": 2,
                        "angle": 0,
                    },
                ]
            }
        )
    )

    await assert_command(
        GetAreaParameter(),
        json,
        (
            firmware_event,
            AreaParameterEvent(
                [
                    AreaParameter(
                        area_id="2",
                        mow_height_level=10,
                        cut_mode=7,
                        obstacle_height=1,
                        angle=180,
                    ),
                    AreaParameter(
                        area_id="3",
                        mow_height_level=9,
                        cut_mode=4,
                        obstacle_height=2,
                        angle=0,
                    ),
                ]
            ),
        ),
    )
