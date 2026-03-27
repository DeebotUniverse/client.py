"""Base messages."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum, auto
import functools
from typing import TYPE_CHECKING, Any, final

import orjson

from deebot_client.events import FirmwareEvent
from deebot_client.util import verify_required_class_variables_exists

from .logging_filter import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from .command import Command
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
    requested_commands: list[Command] = field(default_factory=list)

    @classmethod
    def success(cls) -> HandlingResult:
        """Create result with handling success."""
        return HandlingResult(HandlingState.SUCCESS)

    @classmethod
    def analyse(cls) -> HandlingResult:
        """Create result with handling analyse."""
        return HandlingResult(HandlingState.ANALYSE)


def _handle_error_or_analyse[M: Message, T](
    func: Callable[[type[M], EventBus, T], HandlingResult],
) -> Callable[[type[M], EventBus, T], HandlingResult]:
    """Handle error or None response."""

    @functools.wraps(func)
    def wrapper(cls: type[M], event_bus: EventBus, data: T) -> HandlingResult:
        try:
            response = func(cls, event_bus, data)
        except Exception:
            _LOGGER.warning("Could not parse %s: %s", cls.NAME, data, exc_info=True)
            return HandlingResult(HandlingState.ERROR)
        else:
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
        """Handle message and notify the correct event subscribers."""

    @classmethod
    @_handle_error_or_analyse
    @final
    def handle(cls, event_bus: EventBus, message: MessagePayloadType) -> HandlingResult:
        """Handle message and notify the correct event subscribers."""
        return cls._handle(event_bus, message)


class MessageStr(Message, ABC):
    """String message."""

    @classmethod
    @abstractmethod
    def _handle_str(cls, event_bus: EventBus, message: str) -> HandlingResult:
        """Handle string message and notify the correct event subscribers."""

    @classmethod
    @_handle_error_or_analyse
    @final
    def _dispatch_str(cls, event_bus: EventBus, message: str) -> HandlingResult:
        return cls._handle_str(event_bus, message)

    @classmethod
    def _handle(
        cls, event_bus: EventBus, message: MessagePayloadType
    ) -> HandlingResult:
        if isinstance(message, bytearray):
            data = bytes(message).decode()
        elif isinstance(message, bytes):
            data = message.decode()
        elif isinstance(message, str):
            data = message
        else:
            return HandlingResult.analyse()

        return cls._dispatch_str(event_bus, data)


class MessageDictOrJson(Message, ABC):
    """Dict or json message."""

    @classmethod
    @abstractmethod
    def _handle_dict(
        cls, event_bus: EventBus, message: dict[str, Any]
    ) -> HandlingResult:
        """Handle dict message and notify the correct event subscribers."""

    @classmethod
    @_handle_error_or_analyse
    @final
    def _dispatch_dict(
        cls, event_bus: EventBus, message: dict[str, Any]
    ) -> HandlingResult:
        return cls._handle_dict(event_bus, message)

    @classmethod
    def _handle(
        cls, event_bus: EventBus, message: MessagePayloadType
    ) -> HandlingResult:
        data = message
        if not isinstance(message, dict):
            try:
                data = orjson.loads(message)
            except Exception:
                _LOGGER.debug(
                    "Could not decode message %s payload %s as JSON",
                    cls.NAME,
                    message,
                )

        if isinstance(data, dict):
            fw_version = data.get("header", {}).get("fwVer")
            if fw_version:
                event_bus.notify(FirmwareEvent(fw_version))

            return cls._dispatch_dict(event_bus, data)

        return HandlingResult.analyse()


class MessageBody(MessageDictOrJson, ABC):
    """Dict message with body attribute."""

    @classmethod
    @abstractmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        """Handle message->body and notify the correct event subscribers."""

    @classmethod
    @_handle_error_or_analyse
    @final
    def _dispatch_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        return cls._handle_body(event_bus, body)

    @classmethod
    def _handle_dict(
        cls, event_bus: EventBus, message: dict[str, Any]
    ) -> HandlingResult:
        body = message.get("body")
        if isinstance(body, dict):
            return cls._dispatch_body(event_bus, body)

        return HandlingResult.analyse()


class MessageBodyData(MessageBody, ABC):
    """Dict message with body->data attribute."""

    @classmethod
    def _handle_body_data(
        cls, event_bus: EventBus, data: dict[str, Any] | list[Any]
    ) -> HandlingResult:
        """Fallback body->data handler."""
        return HandlingResult.analyse()

    @classmethod
    @_handle_error_or_analyse
    @final
    def _dispatch_body_data(
        cls, event_bus: EventBus, data: dict[str, Any] | list[Any]
    ) -> HandlingResult:
        return cls._handle_body_data(event_bus, data)

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        data = body.get("data")
        if data is None:
            return HandlingResult.analyse()

        if isinstance(data, (dict, list)):
            return cls._dispatch_body_data(event_bus, data)

        return HandlingResult.analyse()


class MessageBodyDataDict(MessageBodyData, ABC):
    """Dict message with body->data attribute as dict."""

    @classmethod
    @abstractmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle dict body->data and notify the correct event subscribers."""

    @classmethod
    def _handle_body_data(
        cls, event_bus: EventBus, data: dict[str, Any] | list[Any]
    ) -> HandlingResult:
        if isinstance(data, dict):
            return cls._handle_body_data_dict(event_bus, data)

        return HandlingResult.analyse()


class MessageBodyDataList(MessageBodyData, ABC):
    """Dict message with body->data attribute as list."""

    @classmethod
    @abstractmethod
    def _handle_body_data_list(
        cls, event_bus: EventBus, data: list[Any]
    ) -> HandlingResult:
        """Handle list body->data and notify the correct event subscribers."""

    @classmethod
    def _handle_body_data(
        cls, event_bus: EventBus, data: dict[str, Any] | list[Any]
    ) -> HandlingResult:
        if isinstance(data, list):
            return cls._handle_body_data_list(event_bus, data)

        return HandlingResult.analyse()