"""Base messages."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum, auto
import functools
import json
from typing import TYPE_CHECKING, Any, TypeVar, final

from deebot_client.events import FirmwareEvent
from deebot_client.util import verify_required_class_variables_exists

from .logging_filter import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from .event_bus import EventBus

_LOGGER = get_logger(__name__)

MessagePayloadType = str | bytes | bytearray | dict[str, Any]


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
    def success(cls) -> HandlingResult:
        """Create result with handling success."""
        return HandlingResult(HandlingState.SUCCESS)

    @classmethod
    def analyse(cls) -> HandlingResult:
        """Create result with handling analyse."""
        return HandlingResult(HandlingState.ANALYSE)


_MessageT = TypeVar("_MessageT", bound="Message")
_DataT = TypeVar("_DataT")


def _handle_error_or_analyse(
    func: Callable[[type[_MessageT], EventBus, _DataT], HandlingResult],
) -> Callable[[type[_MessageT], EventBus, _DataT], HandlingResult]:
    """Handle error or None response."""

    @functools.wraps(func)
    def wrapper(
        cls: type[_MessageT], event_bus: EventBus, data: _DataT
    ) -> HandlingResult:
        try:
            response = func(cls, event_bus, data)
            # This happens if for some reason someone calls super() of an ABC where handle is not implemented
            if not response:
                _LOGGER.error(
                    "Handler for message %s: %s returned no response. "
                    "This is a bug should not happen. Please report it.",
                    cls.NAME,
                    data,
                )
                return HandlingResult(HandlingState.ERROR)
            if response.state == HandlingState.ANALYSE:
                _LOGGER.debug("Could not handle %s message: %s", cls.NAME, data)
                return HandlingResult(HandlingState.ANALYSE_LOGGED, response.args)
            if response.state == HandlingState.ERROR:
                _LOGGER.warning("Could not parse %s: %s", cls.NAME, data)
            return response
        except Exception:  # pylint: disable=broad-except
            _LOGGER.warning("Could not parse %s: %s", cls.NAME, data, exc_info=True)
            return HandlingResult(HandlingState.ERROR)

    return wrapper


class Message(ABC):
    """Message."""

    NAME: str

    def __init_subclass__(cls) -> None:
        verify_required_class_variables_exists(cls, ("NAME",))
        return super().__init_subclass__()

    @classmethod
    @abstractmethod
    def _handle(
        cls, event_bus: EventBus, message: MessagePayloadType
    ) -> HandlingResult:
        """Handle message and notify the correct event subscribers.

        :return: A message response
        """

    @classmethod
    @_handle_error_or_analyse
    @final
    def handle(cls, event_bus: EventBus, message: MessagePayloadType) -> HandlingResult:
        """Handle message and notify the correct event subscribers.

        :return: A message response
        """
        return cls._handle(event_bus, message)


class MessageStr(Message, ABC):
    """String message."""

    @classmethod
    @abstractmethod
    def _handle_str(cls, event_bus: EventBus, message: str) -> HandlingResult:
        """Handle string message and notify the correct event subscribers.

        :return: A message response
        """

    @classmethod
    @_handle_error_or_analyse
    @final
    def __handle_str(cls, event_bus: EventBus, message: str) -> HandlingResult:
        return cls._handle_str(event_bus, message)

    @classmethod
    def _handle(
        cls, event_bus: EventBus, message: MessagePayloadType
    ) -> HandlingResult:
        """Handle message and notify the correct event subscribers.

        :return: A message response
        """
        if isinstance(message, bytearray):
            data = bytes(message).decode()
        elif isinstance(message, bytes):
            data = message.decode()
        elif isinstance(message, str):
            data = message
        else:
            return super()._handle(event_bus, message)

        return cls.__handle_str(event_bus, data)


class MessageDictOrJson(Message, ABC):
    """Dict or json message."""

    @classmethod
    @abstractmethod
    def _handle_dict(
        cls, event_bus: EventBus, message: dict[str, Any]
    ) -> HandlingResult:
        """Handle string message and notify the correct event subscribers.

        :return: A message response
        """

    @classmethod
    @_handle_error_or_analyse
    @final
    def __handle_dict(
        cls, event_bus: EventBus, message: dict[str, Any]
    ) -> HandlingResult:
        return cls._handle_dict(event_bus, message)

    @classmethod
    def _handle(
        cls, event_bus: EventBus, message: MessagePayloadType
    ) -> HandlingResult:
        """Handle message and notify the correct event subscribers.

        :return: A message response
        """
        data = message
        if not isinstance(message, dict):
            try:
                data = json.loads(message)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.debug(
                    "Could not decode message %s payload %s as JSON",
                    cls.NAME,
                    message,
                )

        if isinstance(data, dict):
            fw_version = data.get("header", {}).get("fwVer", None)
            if fw_version:
                event_bus.notify(FirmwareEvent(fw_version))

            return cls.__handle_dict(event_bus, data)

        return super()._handle(event_bus, message)


class MessageBody(MessageDictOrJson, ABC):
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
    def _handle_dict(
        cls, event_bus: EventBus, message: dict[str, Any]
    ) -> HandlingResult:
        """Handle message and notify the correct event subscribers.

        :return: A message response
        """
        if "body" in message:
            return cls.__handle_body(event_bus, message["body"])

        return super()._handle_dict(event_bus, message)


class MessageBodyData(MessageBody, ABC):
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
                _LOGGER.debug("Could not handle %s message: %s", cls.NAME, data)
                return HandlingResult(HandlingState.ANALYSE_LOGGED, response.args)
            return response
        except Exception:  # pylint: disable=broad-except
            _LOGGER.warning("Could not parse %s: %s", cls.NAME, data, exc_info=True)
            return HandlingResult(HandlingState.ERROR)

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        """Handle message->body and notify the correct event subscribers.

        :return: A message response
        """
        if "data" in body:
            return cls.__handle_body_data(event_bus, body["data"])

        return super()._handle_body(event_bus, body)


class MessageBodyDataDict(MessageBodyData, ABC):
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


class MessageBodyDataList(MessageBodyData, ABC):
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
