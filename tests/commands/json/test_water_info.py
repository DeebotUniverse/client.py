from typing import Any

import pytest

from deebot_client.commands.json import GetWaterInfo, SetWaterInfo
from deebot_client.events import WaterAmount, WaterInfoEvent
from tests.helpers import (
    get_request_json,
    get_success_body,
    verify_DisplayNameEnum_unique,
)

from . import assert_command, assert_set_command


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
    json = get_request_json(get_success_body(json))
    await assert_command(GetWaterInfo(), json, expected)


async def test_SetWaterInfo() -> None:
    command = SetWaterInfo(WaterAmount.MEDIUM)
    args = {"amount": 2}
    await assert_set_command(command, args, WaterInfoEvent(None, WaterAmount.MEDIUM))
