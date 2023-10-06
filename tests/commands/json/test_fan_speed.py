import pytest

from deebot_client.commands.json import GetFanSpeed, SetFanSpeed
from deebot_client.events import FanSpeedEvent
from deebot_client.events.fan_speed import FanSpeedLevel
from tests.helpers import (
    get_request_json,
    get_success_body,
    verify_DisplayNameEnum_unique,
)

from . import assert_command


def test_FanSpeedLevel_unique() -> None:
    verify_DisplayNameEnum_unique(FanSpeedLevel)


async def test_GetFanSpeed() -> None:
    json = get_request_json(get_success_body({"speed": 2}))
    await assert_command(GetFanSpeed(), json, FanSpeedEvent(FanSpeedLevel.MAX_PLUS))


@pytest.mark.parametrize(
    "value, expected",
    [("quiet", 1000), ("max_plus", 2), (0, 0), (FanSpeedLevel.MAX, 1)],
)
def test_SetFanSpeed(value: str | int | FanSpeedLevel, expected: int) -> None:
    command = SetFanSpeed(value)
    assert command.name == "setSpeed"
    assert command._args == {"speed": expected}
