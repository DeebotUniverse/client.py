"""Charge state commands."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import StateEvent
from deebot_client.message import HandlingResult
from deebot_client.messages.json import OnChargeState
from deebot_client.models import State

from .common import JsonCommandWithMessageHandling
from .const import CODE

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetChargeState(JsonCommandWithMessageHandling, OnChargeState):
    """Get charge state command."""

    name = "getChargeState"

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        if body.get(CODE, 0) == 0:
            # Call this also if code is not in the body
            return super()._handle_body(event_bus, body)

        status: State | None = None
        if body.get("msg") == "fail":
            if body["code"] == "30007":  # Already charging
                status = State.DOCKED
            elif body["code"] in ("3", "5"):
                # 3 -> Bot in stuck state, example dust bin out
                # 5 -> Busy with another command
                status = State.ERROR

        if status:
            event_bus.notify(StateEvent(State.DOCKED))
            return HandlingResult.success()

        return HandlingResult.analyse()
