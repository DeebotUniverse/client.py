"""Charge state commands."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import StateEvent
from deebot_client.message import HandlingResult
from deebot_client.messages.json import OnChargeState
from deebot_client.models import State

from .common import JsonCommandWithMessageHandling
from .const import CHARGE_STATE_FAIL_CHARGING, CHARGE_STATE_FAIL_ERROR

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetChargeState(JsonCommandWithMessageHandling, OnChargeState):
    """Get charge state command."""

    name = "getChargeState"

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        if (code := body.get("code", 0)) == 0:
            # Call this also if code is not in the body
            return super()._handle_body(event_bus, body)

        match body.get("msg", ""), code:
            case ("fail", code) if code in CHARGE_STATE_FAIL_CHARGING:
                # 30007 -> Already charging
                status = State.DOCKED
            case ("fail", code) if code in CHARGE_STATE_FAIL_ERROR:
                # 3 -> Bot in stuck state, example dust bin out
                # 5 -> Busy with another command
                status = State.ERROR
            case _:
                return HandlingResult.analyse()

        event_bus.notify(StateEvent(status))
        return HandlingResult.success()
