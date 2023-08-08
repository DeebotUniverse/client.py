import pytest

from deebot_client.commands import FanSpeedLevel, GetFanSpeed, SetFanSpeed
from deebot_client.events import FanSpeedEvent
from deebot_client.events.fan_speed import FanSpeedLevelXml
from tests.commands import assert_command
from tests.helpers import get_request_json, verify_DisplayNameEnum_unique


def test_FanSpeedLevel_unique() -> None:
    verify_DisplayNameEnum_unique(FanSpeedLevel)


async def test_GetFanSpeed() -> None:
    json = get_request_json({"speed": 2})
    await assert_command(GetFanSpeed(), json, FanSpeedEvent(FanSpeedLevel.MAX_PLUS))


@pytest.mark.parametrize("fan_speed", ['strong', 'standard'])
async def test_GetFanSpeedXml(fan_speed: str) -> None:
    data = {
        "ret": "ok",
        "resp": f"<ctl ret='ok' speed='{fan_speed}' />"
    }

    await assert_command(GetFanSpeed(), data, FanSpeedEvent(FanSpeedLevelXml(fan_speed)))


@pytest.mark.parametrize(
    "value, expected",
    [("quiet", 1000), ("max_plus", 2), (0, 0), (FanSpeedLevel.MAX, 1)],
)
def test_SetFanSpeed(value: str | int | FanSpeedLevel, expected: int) -> None:
    command = SetFanSpeed(value)
    assert command.name == "setSpeed"
    assert command._args == {"speed": expected}
