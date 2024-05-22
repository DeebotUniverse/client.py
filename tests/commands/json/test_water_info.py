from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json import GetWaterInfo, SetWaterInfo
from deebot_client.events import WaterAmount, WaterInfoEvent
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
            {"amount": 4, "sweep_type": 1},
            WaterInfoEvent(WaterAmount.ULTRAHIGH, SweepType.Standard),
        ),        (
            {"sweep_type": 2, "enable": 0},
            WaterInfoEvent(SweepType.Deep, mop_attached=False),
        ),
    ],
)
async def test_GetWaterInfo(json: dict[str, Any], expected: WaterInfoEvent) -> None:
    json = get_request_json(get_success_body(json))
    await assert_command(GetWaterInfo(), json, expected)


@pytest.mark.parametrize(("value"), [WaterAmount.MEDIUM, "medium"])
async def test_SetWaterInfo(value: WaterAmount | str) -> None:
    command = SetWaterInfo(value)
    args = {"amount": 2}
    await assert_set_command(command, args, WaterInfoEvent(WaterAmount.MEDIUM))

@pytest.mark.parametrize(("value"), [SweepType.Standard, "standard"])
async def test_SetWaterInfo(value: SweepType | str) -> None:
    command = SetWaterInfo(value)
    args = {"sweep_type": 1}
    await assert_set_command(command, args, WaterInfoEvent(SweepType.Standard))


def test_SetWaterInfo_inexisting_value() -> None:
    with pytest.raises(
        ValueError, match="'INEXSTING' is not a valid WaterAmount member"
    ):
        SetWaterInfo("inexsting")
