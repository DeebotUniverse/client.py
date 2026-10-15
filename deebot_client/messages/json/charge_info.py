"""Charge info messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import StateEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import State

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnChargeInfo(MessageBodyDataDict):
    """On charge info message."""

    NAME = "onChargeInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        Only "goCharging" is mapped, as "idle" is also send after the docking
        and the docked state is reported by onChargeState.

        :return: A message response
        """
        if data.get("state") == "goCharging":
            event_bus.notify(StateEvent(State.RETURNING))
        return HandlingResult.success()
