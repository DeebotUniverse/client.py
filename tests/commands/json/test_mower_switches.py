"""Tests regarding the mower enable commands."""

from __future__ import annotations

import pytest

from deebot_client.commands.json import (
    GetAutoCutDirection,
    GetRecognization,
    SetAutoCutDirection,
    SetRecognization,
)
from deebot_client.events import AiRecognitionEvent, AutoCutDirectionEvent
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


@pytest.mark.parametrize("value", [False, True])
async def test_GetRecognization(*, value: bool) -> None:
    json, firmware_event = get_request_json(
        get_success_body({"state": 1 if value else 0})
    )
    await assert_command(
        GetRecognization(), json, (firmware_event, AiRecognitionEvent(value))
    )


@pytest.mark.parametrize("value", [False, True])
async def test_SetRecognization(*, value: bool) -> None:
    await assert_set_enable_command(
        SetRecognization(value), AiRecognitionEvent, enabled=value, field_name="state"
    )
