from __future__ import annotations

import pytest

from deebot_client.commands.json import GetSweepMode, SetSweepMode
from deebot_client.events import SweepModeEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetSweepMode(*, value: bool) -> None:
    json = get_request_json(get_success_body({"type": 1 if value else 0}))
    await assert_command(GetSweepMode(), json, SweepModeEvent(value))


@pytest.mark.parametrize("value", [False, True])
async def test_SetSweepMode(*, value: bool) -> None:
    await assert_set_enable_command(
        SetSweepMode(value), SweepModeEvent, enabled=value, field_name="type"
    )
