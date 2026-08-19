from __future__ import annotations

from deebot_client.commands.json import SetAreaParameter

from . import assert_execute_command


async def test_SetAreaParameter() -> None:
    args = {
        "areaID": "2",
        "mowHeightLevel": 10,
        "cutMode": 7,
        "obstacleHeight": 1,
        "angle": 136,
    }

    await assert_execute_command(
        SetAreaParameter(
            area_id="2",
            mow_height_level=10,
            cut_mode=7,
            obstacle_height=1,
            angle=136,
        ),
        args,
    )
