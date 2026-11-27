"""Map state command module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.status import MapStateEvent
from deebot_client.message import HandlingResult

from .common import JsonGetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetMapState(JsonGetCommand):
    """Get map state command."""

    NAME = "getMapState"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        state = data["state"]
        if not isinstance(state, str):
            return HandlingResult.analyse()

        event_bus.notify(MapStateEvent(state=state))
        return HandlingResult.success()
