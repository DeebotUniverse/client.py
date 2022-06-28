from typing import Union

import pytest

from deebot_client.commands import FanSpeedLevel, GetFanSpeed, SetFanSpeed
from deebot_client.events import FanSpeedEvent
from tests.commands import assert_command_requested
from tests.helpers import get_request_json, verify_DisplayNameEnum_unique


def test_FanSpeedLevel_unique() -> None:
    verify_DisplayNameEnum_unique(FanSpeedLevel)


def test_GetFanSpeed_requested() -> None:
    json = get_request_json({"speed": 2})
    assert_command_requested(GetFanSpeed(), json, FanSpeedEvent("max+"))


@pytest.mark.parametrize(
    "value, expected", [("quiet", 1000), ("max+", 2), (0, 0), (FanSpeedLevel.MAX, 1)]
)
def test_SetFanSpeed(value: Union[str, int, FanSpeedLevel], expected: int) -> None:

    command = SetFanSpeed(value)
    assert command.name == "setSpeed"
    assert command.args == {"speed": expected}
