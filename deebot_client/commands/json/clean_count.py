"""Clean count command module."""

from collections.abc import Mapping
from typing import Any

from deebot_client.events import CleanCountEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import CommandWithMessageHandling, EventBus, SetCommand


class GetCleanCount(CommandWithMessageHandling, MessageBodyDataDict):
    """Get clean count command."""

    name = "getCleanCount"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """

        event_bus.notify(CleanCountEvent(count=data["count"]))
        return HandlingResult.success()


class SetCleanCount(SetCommand):
    """Set clean count command."""

    name = "setCleanCount"
    get_command = GetCleanCount

    def __init__(self, count: int, **kwargs: Mapping[str, Any]) -> None:
        super().__init__({"count": count}, **kwargs)
