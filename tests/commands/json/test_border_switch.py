"""Tests regarding border switch commands."""

from __future__ import annotations

import pytest

from deebot_client.commands.json import GetBorderSwitch, SetBorderSwitch
from deebot_client.events import BorderSwitchEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetBorderSwitch(*, value: bool) -> None:
    """Testing get border switch."""
    json = get_request_json(get_success_body({"enable": 1 if value else 0}))
    await assert_command(GetBorderSwitch(), json, BorderSwitchEvent(value))


@pytest.mark.parametrize("value", [False, True])
async def test_SetBorderSwitch(*, value: bool) -> None:
    """Testing set border switch."""
    await assert_set_enable_command(
        SetBorderSwitch(value), BorderSwitchEvent, enabled=value
    )
