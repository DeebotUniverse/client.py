"""Child lock messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import ChildLockEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnChildLock(MessageBodyDataDict):
    """On child lock message."""

    NAME = "onChildLock"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(ChildLockEvent(bool(int(data["on"]))))
        return HandlingResult.success()
