"""Base messages."""
import functools
import logging
from abc import ABC
from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Any, Callable, Dict, List, Optional, Type, Union, final

from .events.event_bus import EventBus

_LOGGER = logging.getLogger(__name__)


class MessageHandling(IntEnum):
    """Message handling enum."""

    SUCCESS = auto()
    FAILED = auto()
    ERROR = auto()
    ANALYSE = auto()
    ANALYSE_LOGGED = auto()


@dataclass(frozen=True)
class MessageResponse:
    """Message response object."""

    handling: MessageHandling
    args: Optional[Dict[str, Any]] = None

    @classmethod
    def success(cls) -> "MessageResponse":
        """Create response with handling success."""
        return MessageResponse(MessageHandling.SUCCESS)

    @classmethod
    def analyse(cls) -> "MessageResponse":
        """Create response with handling analyse."""
        return MessageResponse(MessageHandling.ANALYSE)


def _handle_error_or_analyse(
    func: Callable[[Type["Message"], EventBus, Dict[str, Any]], MessageResponse]
) -> Callable[[Type["Message"], EventBus, Dict[str, Any]], MessageResponse]:
    """Handle error or None response."""

    @functools.wraps(func)
    def wrapper(
        cls: Type["Message"], event_bus: EventBus, data: Dict[str, Any]
    ) -> MessageResponse:
        try:
            response = func(cls, event_bus, data)
            if response.handling == MessageHandling.ANALYSE:
                _LOGGER.debug("Could not handle %s message: %s", cls.name, data)
                return MessageResponse(MessageHandling.ANALYSE_LOGGED, response.args)
            return response
        except Exception:  # pylint: disable=broad-except
            _LOGGER.warning("Could not parse %s: %s", cls.name, data, exc_info=True)
            return MessageResponse(MessageHandling.ERROR)

    return wrapper


class Message(ABC):
    """Message with handling code."""

    # will be overwritten in subclasses
    name = "__invalid__"

    @classmethod
    def _handle_body_data_list(cls, event_bus: EventBus, data: List) -> MessageResponse:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        raise NotImplementedError

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: Dict[str, Any]
    ) -> MessageResponse:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        raise NotImplementedError

    @classmethod
    def _handle_body_data(
        cls, event_bus: EventBus, data: Union[Dict[str, Any], List]
    ) -> MessageResponse:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if isinstance(data, dict):
            return cls._handle_body_data_dict(event_bus, data)

        if isinstance(data, list):
            return cls._handle_body_data_list(event_bus, data)

    @classmethod
    @_handle_error_or_analyse
    @final
    def __handle_body_data(
        cls, event_bus: EventBus, data: Union[Dict[str, Any], List]
    ) -> MessageResponse:
        return cls._handle_body_data(event_bus, data)

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: Dict[str, Any]) -> MessageResponse:
        """Handle message->body and notify the correct event subscribers.

        :return: A message response
        """
        data = body.get("data", body)
        return cls.__handle_body_data(event_bus, data)

    @classmethod
    @_handle_error_or_analyse
    @final
    def __handle_body(
        cls, event_bus: EventBus, body: Dict[str, Any]
    ) -> MessageResponse:
        return cls._handle_body(event_bus, body)

    @classmethod
    @_handle_error_or_analyse
    @final
    def handle(cls, event_bus: EventBus, message: Dict[str, Any]) -> MessageResponse:
        """Handle message and notify the correct event subscribers.

        :return: A message response
        """
        data_body = message.get("body", message)
        return cls.__handle_body(event_bus, data_body)
