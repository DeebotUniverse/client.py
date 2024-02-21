from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.events import ErrorEvent, StateEvent
from deebot_client.message import HandlingState
from deebot_client.messages.json import OnError
from deebot_client.models import State
from tests.helpers import get_message_json, get_success_body
from tests.messages import assert_message

if TYPE_CHECKING:
    from collections.abc import Sequence

    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    ("code", "expected_events", "expected_state"),
    [
        (None, None, HandlingState.ANALYSE_LOGGED),
        (
            0,
            ErrorEvent(0, "NoError: Robot is operational"),
            HandlingState.SUCCESS,
        ),
        (
            105,
            [StateEvent(State.ERROR), ErrorEvent(105, "Stuck: Robot is stuck")],
            HandlingState.SUCCESS,
        ),
    ],
)
async def test_OnError(
    code: int | None,
    expected_events: Event | Sequence[Event] | None,
    expected_state: HandlingState,
) -> None:
    json = get_message_json(
        get_success_body({"code": [code] if code is not None else []})
    )
    assert_message(OnError, json, expected_events, expected_state=expected_state)
