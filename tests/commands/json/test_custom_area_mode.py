from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json import GetCustomAreaMode, SetCustomAreaMode
from deebot_client.events import CustomAreaMode, CustomAreaModeEvent
from tests.helpers import (
    get_request_json,
    get_success_body,
)

from . import assert_command, assert_set_command


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"sweepMode": 0}, CustomAreaModeEvent(CustomAreaMode.STANDARD)),
        ({"sweepMode": 1}, CustomAreaModeEvent(CustomAreaMode.DEEP)),
        ({"sweepMode": 2}, CustomAreaModeEvent(CustomAreaMode.QUICK)),
    ],
)
async def test_GetCustomAreaMode(
    data: dict[str, Any], expected: CustomAreaModeEvent
) -> None:
    json, firmware_event = get_request_json(get_success_body(data))
    await assert_command(GetCustomAreaMode(), json, (firmware_event, expected))


@pytest.mark.parametrize(
    ("value", "raw"),
    [
        (CustomAreaMode.STANDARD, 0),
        (CustomAreaMode.DEEP, 1),
        (CustomAreaMode.QUICK, 2),
        ("standard", 0),
        ("deep", 1),
        ("quick", 2),
    ],
)
async def test_SetCustomAreaMode(value: CustomAreaMode | str, raw: int) -> None:
    command = SetCustomAreaMode(value)
    args = {"sweepMode": raw}
    expected = CustomAreaMode(raw)
    await assert_set_command(command, args, CustomAreaModeEvent(expected))
