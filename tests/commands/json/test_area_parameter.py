from __future__ import annotations

from deebot_client.commands.json import SetAreaParameter

from . import assert_execute_command


async def test_set_area_parameter_defaults() -> None:
    """Test setting area parameters with default values."""
    command = SetAreaParameter(
        area_id=2,
        angle=136,
        mow_height_level=10,
    )

    args = {
        "areaID": "2",
        "mowHeightLevel": 10,
        "cutMode": 7,
        "obstacleHeight": 1,
        "angle": 136,
    }

    await assert_execute_command(command, args)


async def test_set_area_parameter_custom_values() -> None:
    """Test setting area parameters with custom values."""
    command = SetAreaParameter(
        area_id="4",
        angle=90,
        mow_height_level=8,
        cut_mode=3,
        obstacle_height=2,
    )

    args = {
        "areaID": "4",
        "mowHeightLevel": 8,
        "cutMode": 3,
        "obstacleHeight": 2,
        "angle": 90,
    }

    await assert_execute_command(command, args)
