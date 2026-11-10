from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json import GetDryingDuration, SetDryingDuration
from deebot_client.events import DryingDuration, DryingDurationEvent
from tests.helpers import (
    get_request_json,
    get_success_body,
)

from . import assert_command, assert_set_command


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"duration": 120}, DryingDurationEvent(DryingDuration.TWO_HOURS)),
        ({"duration": 180}, DryingDurationEvent(DryingDuration.THREE_HOURS)),
        ({"duration": 240}, DryingDurationEvent(DryingDuration.FOUR_HOURS)),
    ],
)
async def test_GetDryingDuration(
    data: dict[str, Any], expected: DryingDurationEvent
) -> None:
    json, firmware_event = get_request_json(get_success_body(data))
    await assert_command(GetDryingDuration(), json, (firmware_event, expected))


@pytest.mark.parametrize(
    ("value", "raw"),
    [
        (DryingDuration.TWO_HOURS, 120),
        (DryingDuration.THREE_HOURS, 180),
        (DryingDuration.FOUR_HOURS, 240),
        ("two_hours", 120),
        ("three_hours", 180),
        ("four_hours", 240),
    ],
)
async def test_SetDryingDuration(value: DryingDuration | str, raw: int) -> None:
    command = SetDryingDuration(value)
    args = {"duration": raw}
    expected = DryingDuration(raw)
    await assert_set_command(command, args, DryingDurationEvent(expected))
