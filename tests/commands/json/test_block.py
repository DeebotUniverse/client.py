from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json import GetBlock, SetBlock
from deebot_client.events import BlockEvent
from deebot_client.message import HandlingResult, HandlingState
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


@pytest.mark.parametrize(
    "payload",
    [
        {"enable": None, "start": "22:0", "end": "8:0"},
        {"enable": True, "start": "22:0", "end": "8:0"},
        {"enable": False, "start": "22:0", "end": "8:0"},
        {"enable": 1.0, "start": "22:0", "end": "8:0"},
        {"enable": 0.0, "start": "22:0", "end": "8:0"},
        {"enable": 1, "start": None, "end": "8:0"},
        {"enable": 1, "start": "22:0", "end": None},
        {"enable": 2, "start": "22:0", "end": "8:0"},
        {"enable": "0", "start": "22:0", "end": "8:0"},
        {"enable": 1, "start": 220, "end": "8:0"},
    ],
)
async def test_GetBlock_invalid_fields(payload: dict[str, Any]) -> None:
    """Malformed fields must not be coerced into a valid-looking block."""
    json, firmware_event = get_request_json(get_success_body(payload))
    await assert_command(
        GetBlock(),
        json,
        (firmware_event,),
        handling_result=HandlingResult(HandlingState.ANALYSE_LOGGED),
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"start": "22:0", "end": "8:0"},
        {"enable": 1, "end": "8:0"},
        {"enable": 1, "start": "22:0"},
    ],
)
async def test_GetBlock_missing_fields(payload: dict[str, Any]) -> None:
    """Missing fields keep the existing parse-error path."""
    json, firmware_event = get_request_json(get_success_body(payload))
    await assert_command(
        GetBlock(),
        json,
        (firmware_event,),
        handling_result=HandlingResult(HandlingState.ERROR),
    )
