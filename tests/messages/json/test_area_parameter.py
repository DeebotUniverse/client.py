from __future__ import annotations

import pytest

from deebot_client.events import AreaParameter, AreaParameterEvent, FirmwareEvent
from deebot_client.messages.json import OnAreaParameter
from tests.messages.json import assert_message


@pytest.mark.benchmark
def test_onAreaParameter() -> None:
    data = {
        "header": {
            "pri": 1,
            "tzm": 120,
            "ts": "1779831717614",
            "ver": "0.0.1",
            "fwVer": "1.0.0",
            "hwVer": "0.1.1",
        },
        "body": {
            "data": {
                "areaParameters": [
                    {
                        "areaID": "2",
                        "mowHeightLevel": 10,
                        "cutMode": 7,
                        "obstacleHeight": 1,
                        "angle": 136,
                    },
                    {
                        "areaID": "3",
                        "mowHeightLevel": 4,
                        "cutMode": 7,
                        "obstacleHeight": 1,
                        "angle": 180,
                    },
                ]
            }
        },
    }

    assert_message(
        OnAreaParameter,
        data,
        (
            FirmwareEvent("1.0.0"),
            AreaParameterEvent(
                [
                    AreaParameter(
                        area_id="2",
                        mow_height_level=10,
                        cut_mode=7,
                        obstacle_height=1,
                        angle=136,
                    ),
                    AreaParameter(
                        area_id="3",
                        mow_height_level=4,
                        cut_mode=7,
                        obstacle_height=1,
                        angle=180,
                    ),
                ]
            ),
        ),
    )
