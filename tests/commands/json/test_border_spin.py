"""Tests regarding border spin commands."""

from __future__ import annotations

import pytest

from deebot_client.commands.json import GetBorderSpin, SetBorderSpin
from deebot_client.events import BorderSpinEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetBorderSpin(*, value: bool) -> None:
    """Testing get border spin."""
    json, firmware_event = get_request_json(
        get_success_body({"enable": 1 if value else 0})
    )
    await assert_command(
        GetBorderSpin(), json, (firmware_event, BorderSpinEvent(value))
    )


@pytest.mark.parametrize("value", [False, True])
async def test_SetBorderSpin(*, value: bool) -> None:
    """Testing set border spin."""
    await assert_set_enable_command(
        SetBorderSpin(value), BorderSpinEvent, enabled=value
    )
