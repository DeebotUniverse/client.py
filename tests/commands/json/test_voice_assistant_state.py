from __future__ import annotations

import pytest

from deebot_client.commands.json import GetVoiceAssistantState, SetVoiceAssistantState
from deebot_client.events import VoiceAssistantStateEvent
from tests.helpers import get_request_json, get_success_body

from . import assert_command, assert_set_enable_command


@pytest.mark.parametrize("value", [False, True])
async def test_GetVoiceAssistantState(*, value: bool) -> None:
    json, firmware_event = get_request_json(
        get_success_body({"enable": 1 if value else 0})
    )
    await assert_command(
        GetVoiceAssistantState(),
        json,
        (firmware_event, VoiceAssistantStateEvent(value)),
    )


@pytest.mark.parametrize("value", [False, True])
async def test_SetVoiceAssistantState(*, value: bool) -> None:
    await assert_set_enable_command(
        SetVoiceAssistantState(value), VoiceAssistantStateEvent, enabled=value
    )
