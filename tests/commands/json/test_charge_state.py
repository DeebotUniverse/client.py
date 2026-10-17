from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest

from deebot_client.commands.json import GetChargeState
from deebot_client.events import StateEvent
from deebot_client.message import HandlingState
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


@pytest.mark.parametrize("code", [5, "5", 3, "3", 30007, "30007"])
def test_busy_stuck_and_already_charging(code: int | str) -> None:
    bus = Mock()
    bus.get_last_event.return_value = StateEvent(State.IDLE)
    result = GetChargeState._handle_body(bus, {"code": code, "msg": "fail"})
    if str(code) == "5":
        assert result.state == HandlingState.FAILED
        bus.notify.assert_not_called()
    else:
        assert result.state == HandlingState.SUCCESS
        expected = State.ERROR if str(code) == "3" else State.DOCKED
        bus.notify.assert_called_once_with(StateEvent(expected))


@pytest.mark.parametrize(
    "current", [None, State.IDLE, State.RETURNING, State.DOCKED, State.CLEANING]
)
@pytest.mark.parametrize(
    "reply", [{"code": 0, "data": {"isCharging": 1}}, {"code": "30007", "msg": "fail"}]
)
def test_delayed_charging_does_not_override_active_cleaning(
    current: State | None, reply: dict[str, Any]
) -> None:
    bus = Mock()
    bus.get_last_event.return_value = (
        StateEvent(current) if current is not None else None
    )
    result = GetChargeState._handle_body(bus, reply)
    assert result.state == HandlingState.SUCCESS
    if current == State.CLEANING:
        bus.notify.assert_not_called()
    else:
        bus.notify.assert_called_once_with(StateEvent(State.DOCKED))


def test_noncharging_reply_does_not_invent_a_robot_state() -> None:
    bus = Mock()
    result = GetChargeState._handle_body(bus, {"code": 0, "data": {"isCharging": 0}})
    assert result.state == HandlingState.SUCCESS
    bus.notify.assert_not_called()
