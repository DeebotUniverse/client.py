"""Tests regarding moveup warning commands."""
from __future__ import annotations

import pytest

from deebot_client.commands.json import GetMoveUpWarning, SetMoveUpWarning
from deebot_client.events import MoveUpWarningEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetMoveUpWarning(*, value: bool) -> None:
    """Testing get moveup warning."""
    json = get_request_json(get_success_body({"enable": 1 if value else 0}))
    await assert_command(GetMoveUpWarning(), json, MoveUpWarningEvent(value))


@pytest.mark.parametrize("value", [False, True])
async def test_SetMoveUpWarning(*, value: bool) -> None:
    """Testing set moveup warning."""
    await assert_set_enable_command(
        SetMoveUpWarning(value), MoveUpWarningEvent, enabled=value
    )
