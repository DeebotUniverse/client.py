"""Tests regarding cross map border warning commands."""
from __future__ import annotations

import pytest

from deebot_client.commands.json import (
    GetCrossMapBorderWarning,
    SetCrossMapBorderWarning,
)
from deebot_client.events import CrossMapBorderWarningEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetCrossMapBorderWarning(*, value: bool) -> None:
    """Testing get cross map border warning."""
    json = get_request_json(get_success_body({"enable": 1 if value else 0}))
    await assert_command(
        GetCrossMapBorderWarning(), json, CrossMapBorderWarningEvent(value)
    )


@pytest.mark.parametrize("value", [False, True])
async def test_SetCrossMapBorderWarning(*, value: bool) -> None:
    """Testing set cross map border warning."""
    await assert_set_enable_command(
        SetCrossMapBorderWarning(value), CrossMapBorderWarningEvent, enabled=value
    )
