"""Tests regarding cut efficiency commands."""

from __future__ import annotations

import pytest

from deebot_client.commands.json import GetCutEfficiency, SetCutEfficiency
from deebot_client.events.mower import CutEfficiency, CutEfficiencyEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_command


@pytest.mark.parametrize("efficiency", [CutEfficiency.EFFICIENT, CutEfficiency.FINE])
async def test_GetCutEfficiency(efficiency: CutEfficiency) -> None:
    json, firmware_event = get_request_json(
        get_success_body({"level": efficiency.value})
    )
    await assert_command(
        GetCutEfficiency(),
        json,
        (firmware_event, CutEfficiencyEvent(efficiency)),
        device_class="2px96q",
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (CutEfficiency.EFFICIENT, CutEfficiency.EFFICIENT),
        ("fine", CutEfficiency.FINE),
    ],
)
async def test_SetCutEfficiency(
    value: CutEfficiency | str, expected: CutEfficiency
) -> None:
    await assert_set_command(
        SetCutEfficiency(value),
        {"level": expected.value},
        CutEfficiencyEvent(expected),
    )
