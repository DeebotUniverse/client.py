from __future__ import annotations

from unittest.mock import Mock

import pytest

from deebot_client.commands.json import GetCleanPreference, SetCleanPreference
from deebot_client.commands.json.xwk78e import GetCleanPreferenceT80
from deebot_client.events import CleanPreferenceEvent
from deebot_client.message import HandlingResult
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetCleanPreference(*, value: bool) -> None:
    json, firmware_event = get_request_json(
        get_success_body({"enable": 1 if value else 0})
    )
    await assert_command(
        GetCleanPreference(), json, (firmware_event, CleanPreferenceEvent(value))
    )


async def test_GetCleanPreference_unsupported_read_service() -> None:
    result = GetCleanPreferenceT80._handle_body(
        Mock(), {"code": 20005, "msg": "call setting service empty"}
    )

    assert result == HandlingResult.success()


@pytest.mark.parametrize("value", [False, True])
async def test_SetCleanPreference(*, value: bool) -> None:
    await assert_set_enable_command(
        SetCleanPreference(value), CleanPreferenceEvent, enabled=value
    )
