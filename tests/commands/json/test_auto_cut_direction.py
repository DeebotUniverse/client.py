"""Tests regarding the auto cut direction commands."""

from __future__ import annotations

import pytest

from deebot_client.commands.json import (
    GetAutoCutDirection,
    SetAutoCutDirection,
)
from deebot_client.events import AutoCutDirectionEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetAutoCutDirection(*, value: bool) -> None:
    json, firmware_event = get_request_json(
        get_success_body({"enable": 1 if value else 0})
    )
    await assert_command(
        GetAutoCutDirection(), json, (firmware_event, AutoCutDirectionEvent(value))
    )


@pytest.mark.parametrize("value", [False, True])
async def test_SetAutoCutDirection(*, value: bool) -> None:
    await assert_set_enable_command(
        SetAutoCutDirection(value), AutoCutDirectionEvent, enabled=value
    )
