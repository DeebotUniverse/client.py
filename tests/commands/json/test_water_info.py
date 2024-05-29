from __future__ import annotations

import re
from typing import Any

import pytest

from deebot_client.commands.json import GetWaterInfo, SetWaterInfo
from deebot_client.events import SweepType, WaterAmount, WaterInfoEvent
from tests.helpers import (
    get_request_json,
    get_success_body,
)

from . import assert_command, assert_set_command


@pytest.mark.parametrize(
    ("json", "expected"),
    [
        ({"amount": 2}, WaterInfoEvent(WaterAmount.MEDIUM)),
        (
            {"amount": 1, "enable": 1},
            WaterInfoEvent(WaterAmount.LOW, mop_attached=True),
        ),
        (
            {"amount": 4, "enable": 0},
            WaterInfoEvent(WaterAmount.ULTRAHIGH, mop_attached=False),
        ),
        (
            {"amount": 4, "sweepType": 1, "enable": 0},
            WaterInfoEvent(
                WaterAmount.ULTRAHIGH, SweepType.STANDARD, mop_attached=False
            ),
        ),
        (
            {"amount": 4, "sweepType": 2, "enable": 0},
            WaterInfoEvent(WaterAmount.ULTRAHIGH, SweepType.DEEP, mop_attached=False),
        ),
    ],
)
async def test_GetWaterInfo(json: dict[str, Any], expected: WaterInfoEvent) -> None:
    json = get_request_json(get_success_body(json))
    await assert_command(GetWaterInfo(), json, expected)


@pytest.mark.parametrize(("water_value"), [WaterAmount.MEDIUM, "medium"])
@pytest.mark.parametrize(("sweep_value"), [SweepType.STANDARD, "standard", None])
async def test_SetWaterInfo_Wateramount(
    water_value: WaterAmount | str, sweep_value: SweepType | str | None
) -> None:
    command = SetWaterInfo(water_value, sweep_value)
    args = {"amount": 2}
    if sweep_value:
        args["sweepType"] = 1
    await assert_set_command(
        command,
        args,
        WaterInfoEvent(WaterAmount.MEDIUM, SweepType.STANDARD if sweep_value else None),
    )


@pytest.mark.parametrize(
    ("command_values", "error", "error_message"),
    [
        (
            {"bla": "inexsting"},
            TypeError,
            re.escape(
                "SetWaterInfo.__init__() got an unexpected keyword argument 'bla'"
            ),
        ),
        (
            {"amount": "inexsting"},
            ValueError,
            "'INEXSTING' is not a valid WaterAmount member",
        ),
        (
            {"amount": WaterAmount.HIGH, "sweep_type": "inexsting"},
            ValueError,
            "'INEXSTING' is not a valid SweepType member",
        ),
    ],
)
def test_SetWaterInfo_inexisting_value(
    command_values: dict[str, Any], error: type[Exception], error_message: str
) -> None:
    with pytest.raises(error, match=error_message):
        SetWaterInfo(**command_values)
