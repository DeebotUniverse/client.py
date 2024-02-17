from __future__ import annotations

from typing import Any

import pytest

from deebot_client.events import StateEvent
from deebot_client.message import HandlingState
from deebot_client.messages.json import OnCleanInfo, OnCleanInfoV2
from deebot_client.models import State
from tests.helpers import get_message_json, get_success_body
from tests.messages import assert_message


@pytest.mark.parametrize(
    ("data", "expected_event", "expected_state"),
    [
        ({"trigger": "none"}, None, HandlingState.ANALYSE_LOGGED),
        ({"trigger": "alert"}, StateEvent(State.ERROR), HandlingState.SUCCESS),
        (
            {"trigger": "none", "state": "idle"},
            StateEvent(State.IDLE),
            HandlingState.SUCCESS,
        ),
        (
            {"trigger": "none", "state": "goCharging"},
            StateEvent(State.RETURNING),
            HandlingState.SUCCESS,
        ),
        (
            {
                "trigger": "none",
                "state": "clean",
                "cleanState": {"motionState": "working"},
            },
            StateEvent(State.CLEANING),
            HandlingState.SUCCESS,
        ),
        (
            {
                "trigger": "none",
                "state": "clean",
                "cleanState": {"motionState": "pause"},
            },
            StateEvent(State.PAUSED),
            HandlingState.SUCCESS,
        ),
        (
            {
                "trigger": "none",
                "state": "clean",
                "cleanState": {"motionState": "goCharging"},
            },
            StateEvent(State.RETURNING),
            HandlingState.SUCCESS,
        ),
    ],
)
async def test_OnCleanInfo(
    data: dict[str, Any], expected_event: StateEvent, expected_state: HandlingState
) -> None:
    json = get_message_json(get_success_body(data))
    assert_message(OnCleanInfo, json, expected_event, expected_state=expected_state)
    assert_message(OnCleanInfoV2, json, expected_event, expected_state=expected_state)
