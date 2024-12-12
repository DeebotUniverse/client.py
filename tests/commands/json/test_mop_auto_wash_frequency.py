from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json import GetMopAutoWashFrequency, SetMopAutoWashFrequency
from deebot_client.events import MopAutoWashFrequency, MopAutoWashFrequencyEvent
from tests.helpers import (
    get_request_json,
    get_success_body,
)

from . import assert_command, assert_set_command


@pytest.mark.parametrize(
    ("json", "expected"),
    [
        ({"interval": 10}, MopAutoWashFrequencyEvent(MopAutoWashFrequency.TEN_MINUTES)),
        ({"interval": 15}, MopAutoWashFrequencyEvent(MopAutoWashFrequency.FIFTEEN_MINUTES)),
        ({"interval": 25}, MopAutoWashFrequencyEvent(MopAutoWashFrequency.TWENTY_FIVE_MINUTES)),
    ],
)
async def test_GetMopAutoWashFrequency(
    json: dict[str, Any], expected: MopAutoWashFrequencyEvent
) -> None:
    json = get_request_json(get_success_body(json))
    await assert_command(GetMopAutoWashFrequency(), json, expected)


@pytest.mark.parametrize(("value"), [MopAutoWashFrequency.TEN_MINUTES, "10"])
async def test_SetMopAutoWashFrequency(value: MopAutoWashFrequency | str) -> None:
    command = SetMopAutoWashFrequency(value)
    args = {"interval": 10}
    await assert_set_command(
        command, args, MopAutoWashFrequencyEvent(MopAutoWashFrequency.TEN_MINUTES)
    )