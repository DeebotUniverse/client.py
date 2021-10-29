"""Base messages."""
from abc import ABC
from typing import Any, Dict, List, Union

from .events.event_bus import EventBus


class Message(ABC):
    """Message with handling code."""

    # will be overwritten in subclasses
    name = "__invalid__"

    @classmethod
    def _handle_body_data_list(cls, event_bus: EventBus, data: List) -> bool:
        """Handle message->body->data and notify the correct event subscribers.

        :return: True if data was valid and no error was included
        """
        raise NotImplementedError

    @classmethod
    def _handle_body_data_dict(cls, event_bus: EventBus, data: Dict[str, Any]) -> bool:
        """Handle message->body->data and notify the correct event subscribers.

        :return: True if data was valid and no error was included
        """
        raise NotImplementedError

    @classmethod
    def _handle_body_data(
        cls, event_bus: EventBus, data: Union[Dict[str, Any], List]
    ) -> bool:
        """Handle message->body->data and notify the correct event subscribers.

        :return: True if data was valid and no error was included
        """
        if isinstance(data, dict):
            return cls._handle_body_data_dict(event_bus, data)

        if isinstance(data, list):
            return cls._handle_body_data_list(event_bus, data)

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: Dict[str, Any]) -> bool:
        """Handle message->body and notify the correct event subscribers.

        :return: True if data was valid and no error was included
        """
        data = body.get("data", body)
        return cls._handle_body_data(event_bus, data)

    @classmethod
    def handle(cls, event_bus: EventBus, message: Dict[str, Any]) -> bool:
        """Handle message and notify the correct event subscribers.

        :return: True if data was valid and no error was included
        """
        data_body = message.get("body", message)
        return cls._handle_body(event_bus, data_body)
