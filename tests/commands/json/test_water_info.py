from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.commands.json import GetWaterInfo, SetWaterInfo
from deebot_client.events.water_info import (
    MopAttachedEvent,
    SweepType,
    WaterAmount,
    WaterAmountEvent,
    WaterSweepTypeEvent,
)
from tests.helpers import (
    get_request_json,
    get_success_body,
)

from . import assert_command, assert_set_command

if TYPE_CHECKING:
    from deebot_client.events import Event


@pytest.mark.parametrize(
    ("json", "expected"),
    [
        ({"amount": 2}, (WaterAmountEvent(WaterAmount.MEDIUM),)),
        (
            {"amount": 1, "enable": 1},
            (
                WaterAmountEvent(WaterAmount.LOW),
                MopAttachedEvent(True),
            ),
        ),
        (
            {"amount": 4, "enable": 0},
            (
                WaterAmountEvent(WaterAmount.ULTRAHIGH),
                MopAttachedEvent(False),
            ),
        ),
        (
            {"amount": 4, "sweepType": 1, "enable": 0},
            (
                WaterAmountEvent(WaterAmount.ULTRAHIGH),
                MopAttachedEvent(False),
                WaterSweepTypeEvent(SweepType.STANDARD),
            ),
        ),
        (
            {"amount": 4, "sweepType": 2, "enable": 0},
            (
                WaterAmountEvent(WaterAmount.ULTRAHIGH),
                MopAttachedEvent(False),
                WaterSweepTypeEvent(SweepType.DEEP),
            ),
        ),
    ],
)
async def test_GetWaterInfo(json: dict[str, Any], expected: tuple[Event, ...]) -> None:
    json, firmware_event = get_request_json(get_success_body(json))
    await assert_command(GetWaterInfo(), json, (firmware_event, *expected))


@pytest.mark.parametrize(("water_value"), [WaterAmount.MEDIUM, "medium"])
@pytest.mark.parametrize(("sweep_value"), [SweepType.STANDARD, "standard", None])
async def test_SetWaterInfo_Wateramount(
    water_value: WaterAmount | str, sweep_value: SweepType | str | None
) -> None:
    command = SetWaterInfo(water_value, sweep_value)
    args = {"amount": 2}
    expected_events: list[Event] = [
        WaterAmountEvent(WaterAmount.MEDIUM),
    ]
    if sweep_value:
        args["sweepType"] = 1
        expected_events.append(WaterSweepTypeEvent(SweepType.STANDARD))
    await assert_set_command(command, args, expected_events)


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
