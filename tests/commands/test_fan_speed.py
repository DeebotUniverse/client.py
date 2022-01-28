from typing import Union

import pytest

from deebot_client.commands import FanSpeedLevel, GetFanSpeed, SetFanSpeed
from deebot_client.events import FanSpeedEvent
from tests.commands import assert_command_requested
from tests.helpers import verify_DisplayNameEnum_unique


def test_FanSpeedLevel_unique():
    verify_DisplayNameEnum_unique(FanSpeedLevel)


def test_GetFanSpeed_requested():
    data = {
        "id": "WiQO",
        "ret": "ok",
        "resp": {
            "header": {
                "pri": 1,
                "tzm": 480,
                "ts": "1305336289055",
                "ver": "0.0.1",
                "fwVer": "1.8.2",
                "hwVer": "0.1.1",
            },
            "body": {"code": 0, "msg": "ok", "data": {"speed": 2}},
        },
    }

    assert_command_requested(GetFanSpeed(), data, FanSpeedEvent("max+"))


@pytest.mark.parametrize(
    "value, expected", [("quiet", 1000), ("max+", 2), (0, 0), (FanSpeedLevel.MAX, 1)]
)
def test_SetFanSpeed(value: Union[str, int, FanSpeedLevel], expected: int):

    command = SetFanSpeed(value)
    assert command.name == "setSpeed"
    assert command.args == {"speed": expected}
