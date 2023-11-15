"""Base messages."""
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum, auto
import functools
from typing import Any, TypeVar, final

from .event_bus import EventBus
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


_MessageT = TypeVar("_MessageT", bound="Message")


def _handle_error_or_analyse(
    func: Callable[[type[_MessageT], EventBus, dict[str, Any]], HandlingResult]
) -> Callable[[type[_MessageT], EventBus, dict[str, Any]], HandlingResult]:
    """Handle error or None response."""

    @functools.wraps(func)
    def wrapper(
        cls: type[_MessageT], event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        try:
            response = func(cls, event_bus, data)
            if response.state == HandlingState.ANALYSE:
                _LOGGER.debug("Could not handle %s message: %s", cls.name, data)
                return HandlingResult(HandlingState.ANALYSE_LOGGED, response.args)
            if response.state == HandlingState.ERROR:
                _LOGGER.warning("Could not parse %s: %s", cls.name, data)
            return response
        except Exception:  # pylint: disable=broad-except
            _LOGGER.warning("Could not parse %s: %s", cls.name, data, exc_info=True)
            return HandlingResult(HandlingState.ERROR)

    return wrapper


class Message(ABC):
    """Message."""

    @property  # type: ignore[misc]
    @classmethod
    @abstractmethod
    def name(cls) -> str:
        """Command name."""

    @classmethod
    @abstractmethod
    def _handle(
        cls, event_bus: EventBus, message: dict[str, Any] | str
    ) -> HandlingResult:
        """Handle message and notify the correct event subscribers.

        :return: A message response
        """

    @classmethod
    @_handle_error_or_analyse
    @final
    def handle(
        cls, event_bus: EventBus, message: dict[str, Any] | str
    ) -> HandlingResult:
        """Handle message and notify the correct event subscribers.

        :return: A message response
        """
        return cls._handle(event_bus, message)


class MessageStr(Message):
    """String message."""

    @classmethod
    @abstractmethod
    def _handle_str(cls, event_bus: EventBus, message: str) -> HandlingResult:
        """Handle string message and notify the correct event subscribers.

        :return: A message response
        """

    @classmethod
    # @_handle_error_or_analyse @edenhaus will make the decorator to work again
    @final
    def __handle_str(cls, event_bus: EventBus, message: str) -> HandlingResult:
        return cls._handle_str(event_bus, message)

    @classmethod
    def _handle(
        cls, event_bus: EventBus, message: dict[str, Any] | str
    ) -> HandlingResult:
        """Handle message and notify the correct event subscribers.

        :return: A message response
        """

        # This basically means an XML message
        if isinstance(message, str):
            return cls.__handle_str(event_bus, message)

        return super()._handle(event_bus, message)


class MessageBody(Message):
    """Dict message with body attribute."""

    @classmethod
    @abstractmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        """Handle message->body and notify the correct event subscribers.

        :return: A message response
        """

    @classmethod
    @_handle_error_or_analyse
    @final
    def __handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        return cls._handle_body(event_bus, body)

    @classmethod
    def _handle(
        cls, event_bus: EventBus, message: dict[str, Any] | str
    ) -> HandlingResult:
        """Handle message and notify the correct event subscribers.

        :return: A message response
        """
        if isinstance(message, dict):
            return cls.__handle_body(event_bus, message["body"])

        return super()._handle(event_bus, message)


class MessageBodyData(MessageBody):
    """Dict message with body->data attribute."""

    @classmethod
    @abstractmethod
    def _handle_body_data(
        cls, event_bus: EventBus, data: dict[str, Any] | list[Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """

    @classmethod
    @final
    def __handle_body_data(
        cls, event_bus: EventBus, data: dict[str, Any] | list[Any]
    ) -> HandlingResult:
        try:
            response = cls._handle_body_data(event_bus, data)
            if response.state == HandlingState.ANALYSE:
                _LOGGER.debug("Could not handle %s message: %s", cls.name, data)
                return HandlingResult(HandlingState.ANALYSE_LOGGED, response.args)
            return response
        except Exception:  # pylint: disable=broad-except
            _LOGGER.warning("Could not parse %s: %s", cls.name, data, exc_info=True)
            return HandlingResult(HandlingState.ERROR)

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        """Handle message->body and notify the correct event subscribers.

        :return: A message response
        """
        if "data" in body:
            return cls.__handle_body_data(event_bus, body["data"])

        return super()._handle_body(event_bus, body)


class MessageBodyDataDict(MessageBodyData):
    """Dict message with body->data attribute as dict."""

    @classmethod
    @abstractmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """

    @classmethod
    def _handle_body_data(
        cls, event_bus: EventBus, data: dict[str, Any] | list[Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if isinstance(data, dict):
            return cls._handle_body_data_dict(event_bus, data)

        return super()._handle_body_data(event_bus, data)


class MessageBodyDataList(MessageBodyData):
    """Dict message with body->data attribute as list."""

    @classmethod
    @abstractmethod
    def _handle_body_data_list(
        cls, event_bus: EventBus, data: list[Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """

    @classmethod
    def _handle_body_data(
        cls, event_bus: EventBus, data: dict[str, Any] | list[Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if isinstance(data, list):
            return cls._handle_body_data_list(event_bus, data)

        return super()._handle_body_data(event_bus, data)
