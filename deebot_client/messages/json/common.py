"""Common json messages."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any

from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.util import verify_required_class_variables_exists

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus
    from deebot_client.events import EnableEvent


class OnEnableMessage(MessageBodyDataDict, ABC):
    """Abstract on enable message."""

    _field_name: str = "enable"
    EVENT_TYPE: type[EnableEvent]

    def __init_subclass__(cls) -> None:
        verify_required_class_variables_exists(cls, ("EVENT_TYPE",))
        return super().__init_subclass__()

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event: EnableEvent = cls.EVENT_TYPE(bool(data[cls._field_name]))
        event_bus.notify(event)
        return HandlingResult.success()
