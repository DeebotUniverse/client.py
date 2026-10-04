"""Charge state commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import StateEvent
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataDict
from deebot_client.models import State

from .common import JsonCommandWithMessageHandling
from .const import CODE

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetChargeState(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get charge state command."""

    NAME = "getChargeState"

    @staticmethod
    def _notify_docked(event_bus: EventBus) -> None:
        # Charging readback can lag departure after mop preparation. An active
        # clean-state report takes precedence until idle/return/washing reports.
        current = event_bus.get_last_event(StateEvent)
        if current is None or current.state != State.CLEANING:
            event_bus.notify(StateEvent(State.DOCKED))

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if data.get("isCharging") == 1:
            cls._notify_docked(event_bus)
        return HandlingResult.success()

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        if body.get(CODE, 0) == 0:
            # Call this also if code is not in the body
            return super()._handle_body(event_bus, body)

        if body.get("msg") == "fail":
            code = str(body.get(CODE))
            if code == "30007":  # Already charging
                cls._notify_docked(event_bus)
                return HandlingResult.success()
            if code == "3":  # Stuck, for example dust bin out
                event_bus.notify(StateEvent(State.ERROR))
                return HandlingResult.success()
            if code == "5":  # Query rejected while busy; no robot-state evidence
                return HandlingResult(HandlingState.FAILED)

        return HandlingResult.analyse()
