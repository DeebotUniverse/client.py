"""Tests regarding child lock commands."""

from __future__ import annotations

import pytest

from deebot_client.commands.json import GetChildLock, SetChildLock
from deebot_client.events import ChildLockEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetChildLock(*, value: bool) -> None:
    """Testing get child lock."""
    json = get_request_json(get_success_body({"on": 1 if value else 0}))
    await assert_command(GetChildLock(), json, ChildLockEvent(value))


@pytest.mark.parametrize("value", [False, True])
async def test_SetChildLock(*, value: bool) -> None:
    """Testing set child lock."""
    await assert_set_enable_command(
        SetChildLock(value), ChildLockEvent, enabled=value, field_name="on"
    )
