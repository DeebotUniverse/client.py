"""Tests regarding safe protect commands."""
from __future__ import annotations

import pytest

from deebot_client.commands.json import GetSafeProtect, SetSafeProtect
from deebot_client.events import SafeProtectEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetSafeProtect(*, value: bool) -> None:
    """Testing get safe protect."""
    json = get_request_json(get_success_body({"enable": 1 if value else 0}))
    await assert_command(GetSafeProtect(), json, SafeProtectEvent(value))


@pytest.mark.parametrize("value", [False, True])
async def test_SetSafeProtect(*, value: bool) -> None:
    """Testing set safe protect."""
    await assert_set_enable_command(
        SetSafeProtect(value), SafeProtectEvent, enabled=value
    )
