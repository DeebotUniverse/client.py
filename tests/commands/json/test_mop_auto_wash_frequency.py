from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json import GetMopAutoWashFrequency, SetMopAutoWashFrequency
from deebot_client.events.mop_auto_wash_frequency import MopAutoWashFrequencyEvent
from tests.helpers import (
    get_request_json,
    get_success_body,
)

from . import assert_command, assert_set_command


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"interval": 10}, MopAutoWashFrequencyEvent(10)),
        (
            {"interval": 15},
            MopAutoWashFrequencyEvent(15),
        ),
        (
            {"interval": 25},
            MopAutoWashFrequencyEvent(25),
        ),
    ],
)
async def test_GetMopAutoWashFrequency(
    data: dict[str, Any], expected: MopAutoWashFrequencyEvent
) -> None:
    json, firmware_event = get_request_json(get_success_body(data))
    await assert_command(GetMopAutoWashFrequency(), json, (firmware_event, expected))


@pytest.mark.parametrize(("value"), [10, 15, 25])
async def test_SetMopAutoWashFrequency(value: int) -> None:
    command = SetMopAutoWashFrequency(value)
    args = {"interval": value}
    await assert_set_command(command, args, MopAutoWashFrequencyEvent(value))
