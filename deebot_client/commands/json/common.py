"""Base commands."""
from abc import ABC, abstractmethod
from datetime import datetime
from types import MappingProxyType
from typing import Any

from deebot_client.command import (
    Command,
    CommandWithMessageHandling,
    InitParam,
    SetCommand,
)
from deebot_client.const import DataType
from deebot_client.event_bus import EventBus
from deebot_client.events import EnableEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import (
    HandlingResult,
    HandlingState,
    MessageBodyDataDict,
)

from .const import CODE

_LOGGER = get_logger(__name__)


class JsonCommand(Command):
    """Json base command."""

    data_type: DataType = DataType.JSON

    def _get_payload(self) -> dict[str, Any] | list[Any]:
        payload = {
            "header": {
                "pri": "1",
                "ts": datetime.now().timestamp(),
                "tzm": 480,
                "ver": "0.0.50",
            }
        }

        if len(self._args) > 0:
            payload["body"] = {"data": self._args}

        return payload


class JsonCommandWithMessageHandling(JsonCommand, CommandWithMessageHandling, ABC):
    """Command, which handle response by itself."""


class ExecuteCommand(JsonCommandWithMessageHandling, ABC):
    """Command, which is executing something (ex. Charge)."""

    @classmethod
    def _handle_body(cls, _: EventBus, body: dict[str, Any]) -> HandlingResult:
        """Handle message->body and notify the correct event subscribers.

        :return: A message response
        """
        # Success event looks like { "code": 0, "msg": "ok" }
        if body.get(CODE, -1) == 0:
            return HandlingResult.success()

        _LOGGER.warning('Command "%s" was not successfully. body=%s', cls.name, body)
        return HandlingResult(HandlingState.FAILED)


class JsonSetCommand(ExecuteCommand, SetCommand, ABC):
    """Json base set command.

    Command needs to be linked to the "get" command, for handling (updating) the sensors.
    """


class GetEnableCommand(JsonCommandWithMessageHandling, MessageBodyDataDict, ABC):
    """Abstract get enable command."""

    @property  # type: ignore[misc]
    @classmethod
    @abstractmethod
    def event_type(cls) -> type[EnableEvent]:
        """Event type."""

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event: EnableEvent = cls.event_type(bool(data["enable"]))  # type: ignore[call-arg, assignment]
        event_bus.notify(event)
        return HandlingResult.success()


class SetEnableCommand(JsonSetCommand, ABC):
    """Abstract set enable command."""

    _mqtt_params = MappingProxyType({"enable": InitParam(bool)})

    def __init__(self, enable: bool) -> None:  # noqa: FBT001
        super().__init__({"enable": 1 if enable else 0})
