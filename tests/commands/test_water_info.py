from typing import Any

import pytest

from deebot_client.commands import GetWaterInfo, SetWaterInfo
from deebot_client.events import WaterAmount, WaterInfoEvent
from tests.commands import assert_command_requested, assert_set_command
from tests.helpers import get_request_json, verify_DisplayNameEnum_unique


def test_WaterAmount_unique() -> None:
    verify_DisplayNameEnum_unique(WaterAmount)


@pytest.mark.parametrize(
    "json, expected",
    [
        ({"amount": 2}, WaterInfoEvent(None, WaterAmount.MEDIUM)),
        ({"amount": 1, "enable": 1}, WaterInfoEvent(True, WaterAmount.LOW)),
        ({"amount": 4, "enable": 0}, WaterInfoEvent(False, WaterAmount.ULTRAHIGH)),
    ],
)
def test_GetWaterInfo_requested(json: dict[str, Any], expected: WaterInfoEvent) -> None:
    json = get_request_json(json)
    assert_command_requested(GetWaterInfo(), json, expected)


@pytest.mark.parametrize(
    "value, expected",
    [
        (WaterAmount.MEDIUM, WaterInfoEvent(None, WaterAmount.MEDIUM)),
        ({"amount": 1, "enable": 1}, WaterInfoEvent(None, WaterAmount.LOW)),
        (4, WaterInfoEvent(None, WaterAmount.ULTRAHIGH)),
        ("low", WaterInfoEvent(None, WaterAmount.LOW)),
    ],
)
def test_SetWaterInfo(
    value: str | int | WaterAmount | dict, expected: WaterInfoEvent
) -> None:
    if isinstance(value, dict):
        command = SetWaterInfo(**value)
    else:
        command = SetWaterInfo(value)

    assert_set_command(command, command.args, expected)
