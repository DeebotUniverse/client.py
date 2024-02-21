from __future__ import annotations

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.json import GetChargeState
from deebot_client.events import StateEvent
from deebot_client.message import HandlingState
from deebot_client.models import State
from tests.helpers import get_request_json, get_success_body

from . import assert_command


@pytest.mark.parametrize(
    ("code", "msg", "is_charging", "expected_event", "expected_state"),
    [
        (0, "ok", 0, None, HandlingState.SUCCESS),
        (0, "ok", 1, StateEvent(State.DOCKED), HandlingState.SUCCESS),
        ("30007", "fail", 1, StateEvent(State.DOCKED), HandlingState.SUCCESS),
        ("3", "fail", 1, StateEvent(State.ERROR), HandlingState.SUCCESS),
        ("5", "fail", 1, StateEvent(State.ERROR), HandlingState.SUCCESS),
        ("666", "fail", 1, None, HandlingState.ANALYSE_LOGGED),
        ("5", "something", 1, None, HandlingState.ANALYSE_LOGGED),
    ],
)
async def test_GetChargeState(
    code: int | str,
    msg: str,
    is_charging: int,
    expected_event: StateEvent | None,
    expected_state: HandlingState,
) -> None:
    json = get_request_json(
        get_success_body({"isCharging": is_charging, "mode": "slot"})
    )
    json["resp"]["body"]["code"] = code
    json["resp"]["body"]["msg"] = msg

    await assert_command(
        GetChargeState(),
        json,
        expected_event,
        command_result=CommandResult(expected_state),
    )
