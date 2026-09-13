from __future__ import annotations

import pytest

from deebot_client.commands.json import GetBlock, SetBlock
from deebot_client.events import BlockEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_command


@pytest.mark.parametrize(
    ("enabled", "start", "end"),
    [
        (False, "22:0", "8:0"),
        (True, "23:30", "7:15"),
    ],
)
async def test_GetBlock(*, enabled: bool, start: str, end: str) -> None:
    json, firmware_event = get_request_json(
        get_success_body({"enable": 1 if enabled else 0, "start": start, "end": end})
    )
    await assert_command(
        GetBlock(), json, (firmware_event, BlockEvent(enabled, start, end))
    )


@pytest.mark.parametrize(
    ("enabled", "start", "end"),
    [
        (False, "22:0", "8:0"),
        (True, "23:30", "7:15"),
    ],
)
async def test_SetBlock(*, enabled: bool, start: str, end: str) -> None:
    await assert_set_command(
        SetBlock(enabled, start, end),
        {"enable": 1 if enabled else 0, "start": start, "end": end},
        [BlockEvent(enabled, start, end)],
    )
