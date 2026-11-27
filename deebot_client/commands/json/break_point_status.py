"""Break-point status command module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.status import BreakPointStatusEvent
from deebot_client.message import HandlingResult

from .common import JsonGetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetBreakPointStatus(JsonGetCommand):
    """Get break-point status command."""

    NAME = "getBreakPointStatus"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        status = data["status"]
        is_conflict = data["isConflict"]
        continue_left_time = data["continueLeftTime"]

        if (
            isinstance(status, bool)
            or not isinstance(status, int)
            or isinstance(continue_left_time, bool)
            or not isinstance(continue_left_time, int)
            or is_conflict not in (0, 1, True, False)
        ):
            return HandlingResult.analyse()

        event_bus.notify(
            BreakPointStatusEvent(
                status=status,
                is_conflict=bool(is_conflict),
                continue_left_time=continue_left_time,
            )
        )
        return HandlingResult.success()
