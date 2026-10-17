"""Relocation state command module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.status import RelocationStateEvent
from deebot_client.message import HandlingResult

from .common import JsonGetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetRelocationState(JsonGetCommand):
    """Get relocation state command."""

    NAME = "getRelocationState"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        has_map = data["isHasMap"]
        mode = data["mode"]
        state = data["state"]

        if (
            has_map not in (0, 1, True, False)
            or not isinstance(mode, str)
            or not isinstance(state, str)
        ):
            return HandlingResult.analyse()

        event_bus.notify(
            RelocationStateEvent(has_map=bool(has_map), mode=mode, state=state)
        )
        return HandlingResult.success()
