from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.commands.json import GetChargeState
from deebot_client.events import StateEvent
from deebot_client.models import State
from tests.helpers import get_request_json, get_success_body

from . import assert_command

if TYPE_CHECKING:
    from deebot_client.events import FirmwareEvent
    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (get_request_json(get_success_body({"isCharging": 0, "mode": "slot"})), None),
    ],
)
async def test_GetChargeState(
    data: tuple[dict[str, Any], FirmwareEvent], expected: StateEvent | None
) -> None:
    json, firmware_event = data
    events: list[Event] = [firmware_event]
    if expected:
        events.append(expected)
    await assert_command(GetChargeState(), json, events)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("30007", StateEvent(State.DOCKED)),
        ("3", StateEvent(State.ERROR)),
        ("5", StateEvent(State.ERROR)),
    ],
)
async def test_GetChargeState_fail(code: str, expected: StateEvent) -> None:
    json, firmware_event = get_request_json({"code": code, "msg": "fail"})
    await assert_command(GetChargeState(), json, (firmware_event, expected))
