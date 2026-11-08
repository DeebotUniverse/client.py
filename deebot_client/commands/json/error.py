"""Error commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.const import ERROR_CODES
from deebot_client.events import Error, ErrorEvent, StateEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import State

from .common import JsonCommandWithMessageHandling

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetError(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get error command."""

    NAME = "getError"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        codes = data.get("code")
        if not isinstance(codes, list):
            return HandlingResult.analyse()

        errors: list[Error] = []
        for code in codes:
            if not isinstance(code, int):
                return HandlingResult.analyse()
            if code != 0:
                errors.append(Error(code, ERROR_CODES.get(code)))

        if errors:
            event_bus.notify(StateEvent(State.ERROR))
        event_bus.notify(ErrorEvent(errors))
        return HandlingResult.success()
