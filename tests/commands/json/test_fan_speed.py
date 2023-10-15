from deebot_client.commands.json import GetFanSpeed, SetFanSpeed
from deebot_client.events import FanSpeedEvent
from deebot_client.events.fan_speed import FanSpeedLevel
from tests.helpers import (
    get_request_json,
    get_success_body,
    verify_DisplayNameEnum_unique,
)

from . import assert_command, assert_set_command


def test_FanSpeedLevel_unique() -> None:
    verify_DisplayNameEnum_unique(FanSpeedLevel)


async def test_GetFanSpeed() -> None:
    json = get_request_json(get_success_body({"speed": 2}))
    await assert_command(GetFanSpeed(), json, FanSpeedEvent(FanSpeedLevel.MAX_PLUS))


async def test_SetFanSpeed() -> None:
    command = SetFanSpeed(FanSpeedLevel.MAX)
    args = {"speed": 1}
    await assert_set_command(command, args, FanSpeedEvent(FanSpeedLevel.MAX))
