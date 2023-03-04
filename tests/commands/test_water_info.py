from typing import Any

import pytest

from deebot_client.commands import GetWaterInfo, SetWaterInfo
from deebot_client.events import WaterAmount, WaterInfoEvent
from tests.commands import assert_command, assert_set_command
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
async def test_GetWaterInfo(json: dict[str, Any], expected: WaterInfoEvent) -> None:
    json = get_request_json(json)
    await assert_command(GetWaterInfo(), json, expected)


@pytest.mark.parametrize(
    "value, exptected_args_amount, expected",
    [
        ("low", 1, WaterInfoEvent(None, WaterAmount.LOW)),
        (WaterAmount.MEDIUM, 2, WaterInfoEvent(None, WaterAmount.MEDIUM)),
        ({"amount": 3, "enable": 1}, 3, WaterInfoEvent(None, WaterAmount.HIGH)),
        (4, 4, WaterInfoEvent(None, WaterAmount.ULTRAHIGH)),
    ],
)
async def test_SetWaterInfo(
    value: str | int | WaterAmount | dict,
    exptected_args_amount: int,
    expected: WaterInfoEvent,
) -> None:
    if isinstance(value, dict):
        command = SetWaterInfo(**value)
    else:
        command = SetWaterInfo(value)

    args = {"amount": exptected_args_amount}
    await assert_set_command(command, args, expected)
