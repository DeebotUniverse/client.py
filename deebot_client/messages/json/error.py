"""Error messages."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.const import ERROR_CODES
from deebot_client.events import ErrorEvent, StateEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import State

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnError(MessageBodyDataDict):
    """On error message."""

    name = "onError"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        # the last error code
        if data := data.get("code", []):
            error = data[-1]
            if error != 0:
                event_bus.notify(StateEvent(State.ERROR))
            event_bus.notify(ErrorEvent(error, ERROR_CODES.get(error)))
            return HandlingResult.success()

        return HandlingResult.analyse()
