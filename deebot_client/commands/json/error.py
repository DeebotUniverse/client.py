"""Error commands."""
from typing import Any

from deebot_client.const import ERROR_CODES
from deebot_client.event_bus import EventBus
from deebot_client.events import ErrorEvent, StateEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import State

from .common import JsonCommandWithMessageHandling


class GetError(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get error command."""

    name = "getError"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        codes = data.get("code", [])
        if codes:
            # the last error code
            error = codes[-1]

            if error is not None:
                description = ERROR_CODES.get(error)
                if error != 0:
                    event_bus.notify(StateEvent(State.ERROR))
                event_bus.notify(ErrorEvent(error, description))
                return HandlingResult.success()

        return HandlingResult.analyse()
