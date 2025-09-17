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
    WaterCustomAmountEvent,
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
        (
            {
                "customAmount": 30,
                "enable": 1,
                "mopCount": 2,
                "sideMop": 0,
                "sweepType": 1,
                "type": 1,
            },
            (
                WaterCustomAmountEvent(30),
                MopAttachedEvent(True),
                WaterSweepTypeEvent(SweepType.STANDARD),
            ),
        ),
    ],
)
async def test_GetWaterInfo(json: dict[str, Any], expected: tuple[Event, ...]) -> None:
    json, firmware_event = get_request_json(get_success_body(json))
    await assert_command(GetWaterInfo(), json, (firmware_event, *expected))


@pytest.mark.parametrize(
    ("command", "args", "expected_events"),
    [
        (
            SetWaterInfo(WaterAmount.MEDIUM),
            {"amount": 2},
            [WaterAmountEvent(WaterAmount.MEDIUM)],
        ),
        (SetWaterInfo("high"), {"amount": 3}, [WaterAmountEvent(WaterAmount.HIGH)]),
        (
            SetWaterInfo(WaterAmount.LOW, sweep_type=SweepType.STANDARD),
            {"amount": 1, "sweepType": 1},
            [
                WaterAmountEvent(WaterAmount.LOW),
                WaterSweepTypeEvent(SweepType.STANDARD),
            ],
        ),
        (
            SetWaterInfo(WaterAmount.ULTRAHIGH, sweep_type="deep"),
            {"amount": 4, "sweepType": 2},
            [
                WaterAmountEvent(WaterAmount.ULTRAHIGH),
                WaterSweepTypeEvent(SweepType.DEEP),
            ],
        ),
        (
            SetWaterInfo(custom_amount=30),
            {"customAmount": 30},
            [WaterCustomAmountEvent(30)],
        ),
        (
            SetWaterInfo(custom_amount=30, sweep_type="deep"),
            {"customAmount": 30, "sweepType": 2},
            [
                WaterCustomAmountEvent(30),
                WaterSweepTypeEvent(SweepType.DEEP),
            ],
        ),
    ],
)
async def test_SetWaterInfo(
    command: SetWaterInfo,
    args: dict[str, Any],
    expected_events: list[Event],
) -> None:
    """Test SetWaterInfo."""
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
        (
            {},
            ValueError,
            "Either amount or custom_amount must be provided.",
        ),
        (
            {"amount": WaterAmount.ULTRAHIGH, "custom_amount": "40"},
            ValueError,
            "Only one of amount or custom_amount can be provided.",
        ),
    ],
)
def test_SetWaterInfo_invalid(
    command_values: dict[str, Any], error: type[Exception], error_message: str
) -> None:
    with pytest.raises(error, match=error_message):
        SetWaterInfo(**command_values)
