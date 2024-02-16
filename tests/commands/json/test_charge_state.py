from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json import GetChargeState
from deebot_client.events import StateEvent
from deebot_client.models import State
from tests.helpers import get_request_json, get_success_body

from . import assert_command

# TODO: check if string codes are really correct


@pytest.mark.parametrize(
    ("code", "msg", "data", "expected"),
    [
        (0, "ok", {"isCharging": 0, "mode": "slot"}, None),
        (0, "ok", {"isCharging": 1, "mode": "slot"}, StateEvent(State.DOCKED)),
        ("30007", "fail", {"isCharging": 1, "mode": "slot"}, StateEvent(State.DOCKED)),
        ("3", "fail", {"isCharging": 1, "mode": "slot"}, StateEvent(State.ERROR)),
        ("5", "fail", {"isCharging": 1, "mode": "slot"}, StateEvent(State.ERROR)),
    ],
)
async def test_GetChargeState(
    code: int | str, msg: str, data: dict[str, Any], expected: StateEvent | None
) -> None:
    json = get_request_json(get_success_body(data))
    json["resp"]["body"]["code"] = code
    json["resp"]["body"]["msg"] = msg

    await assert_command(GetChargeState(), json, expected)
