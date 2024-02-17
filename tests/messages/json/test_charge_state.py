from __future__ import annotations

from typing import Any

import pytest

from deebot_client.events import StateEvent
from deebot_client.messages.json import OnChargeState
from deebot_client.models import State
from tests.helpers import get_message_json, get_success_body
from tests.messages import assert_message


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"isCharging": 0, "mode": "slot"}, None),
        ({"isCharging": 1, "mode": "slot"}, StateEvent(State.DOCKED)),
    ],
)
def test_OnChargeState(data: dict[str, Any], expected: StateEvent | None) -> None:
    json = get_message_json(get_success_body(data))
    assert_message(OnChargeState, json, expected)
