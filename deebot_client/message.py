"""Base messages."""
import functools
from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Any, final

from .events.event_bus import EventBus
from .logging_filter import get_logger

_LOGGER = get_logger(__name__)


class HandlingState(IntEnum):
    """Handling state enum."""

    SUCCESS = auto()
    FAILED = auto()
    ERROR = auto()
    ANALYSE = auto()
    ANALYSE_LOGGED = auto()


@dataclass(frozen=True)
class HandlingResult:
    """Handling result object."""

    state: HandlingState
    args: dict[str, Any] | None = None

    @classmethod
    def success(cls) -> "HandlingResult":
        """Create result with handling success."""
        return HandlingResult(HandlingState.SUCCESS)

    @classmethod
    def analyse(cls) -> "HandlingResult":
        """Create result with handling analyse."""
        return HandlingResult(HandlingState.ANALYSE)


def _handle_error_or_analyse(
    func: Callable[[type["Message"], EventBus, dict[str, Any]], HandlingResult]
) -> Callable[[type["Message"], EventBus, dict[str, Any]], HandlingResult]:
    """Handle error or None response."""

    @functools.wraps(func)
    def wrapper(
        cls: type["Message"], event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        try:
            response = func(cls, event_bus, data)
            if response.state == HandlingState.ANALYSE:
                _LOGGER.debug("Could not handle %s message: %s", cls.name, data)
                return HandlingResult(HandlingState.ANALYSE_LOGGED, response.args)
            return response
        except Exception:  # pylint: disable=broad-except
            _LOGGER.warning("Could not parse %s: %s", cls.name, data, exc_info=True)
            return HandlingResult(HandlingState.ERROR)

    return wrapper


class Message(ABC):
    """Message with handling code."""

    # will be overwritten in subclasses
    name = "__invalid__"

    @classmethod
    def _handle_body_data_list(cls, event_bus: EventBus, data: list) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        raise NotImplementedError

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        raise NotImplementedError

    @classmethod
    def _handle_body_data(
        cls, event_bus: EventBus, data: dict[str, Any] | list
    ) -> HandlingResult:
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
        cls, event_bus: EventBus, data: dict[str, Any] | list
    ) -> HandlingResult:
        return cls._handle_body_data(event_bus, data)

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        """Handle message->body and notify the correct event subscribers.

        :return: A message response
        """
        data = body.get("data", body)
        return cls.__handle_body_data(event_bus, data)

    @classmethod
    @_handle_error_or_analyse
    @final
    def __handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        return cls._handle_body(event_bus, body)

    @classmethod
    @_handle_error_or_analyse
    @final
    def handle(cls, event_bus: EventBus, message: dict[str, Any]) -> HandlingResult:
        """Handle message and notify the correct event subscribers.

        :return: A message response
        """
        data_body = message.get("body", message)
        return cls.__handle_body(event_bus, data_body)
