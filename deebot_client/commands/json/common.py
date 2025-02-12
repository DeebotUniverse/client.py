"""Base commands."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
import json
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import (
    Command,
    CommandMqttP2P,
    CommandWithMessageHandling,
    GetCommand,
    InitParam,
    SetCommand,
)
from deebot_client.const import DataType
from deebot_client.logging_filter import get_logger
from deebot_client.message import (
    HandlingResult,
    HandlingState,
    MessageBody,
    MessageBodyDataDict,
)
from deebot_client.util import verify_required_class_variables_exists

from .const import CODE

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus
    from deebot_client.events import EnableEvent

_LOGGER = get_logger(__name__)


class JsonCommand(Command, ABC):
    """Json base command."""

    DATA_TYPE = DataType.JSON

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


class JsonCommandWithMessageHandling(
    JsonCommand, CommandWithMessageHandling, MessageBody, ABC
):
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

        _LOGGER.warning('Command "%s" was not successfully. body=%s', cls.NAME, body)
        return HandlingResult(HandlingState.FAILED)


class JsonCommandMqttP2P(JsonCommand, CommandMqttP2P, ABC):
    """Json base command for mqtt p2p channel."""

    @classmethod
    def create_from_mqtt(cls, payload: str | bytes | bytearray) -> CommandMqttP2P:
        """Create a command from the mqtt data."""
        payload_json = json.loads(payload)
        data = payload_json["body"]["data"]
        return cls._create_from_mqtt(data)

    def handle_mqtt_p2p(
        self, event_bus: EventBus, response_payload: str | bytes | bytearray
    ) -> None:
        """Handle response received over the mqtt channel "p2p"."""
        response = json.loads(response_payload)
        self._handle_mqtt_p2p(event_bus, response)

    @abstractmethod
    def _handle_mqtt_p2p(self, event_bus: EventBus, response: dict[str, Any]) -> None:
        """Handle response received over the mqtt channel "p2p"."""


class JsonSetCommand(ExecuteCommand, SetCommand, JsonCommandMqttP2P, ABC):
    """Json base set command.

    Command needs to be linked to the "get" command, for handling (updating) the sensors.
    """


class JsonGetCommand(
    JsonCommandWithMessageHandling, MessageBodyDataDict, GetCommand, ABC
):
    """Json get command."""

    @classmethod
    def handle_set_args(
        cls, event_bus: EventBus, args: dict[str, Any]
    ) -> HandlingResult:
        """Handle arguments of set command."""
        return cls._handle_body_data_dict(event_bus, args)


class GetEnableCommand(JsonGetCommand, ABC):
    """Abstract get enable command."""

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


_ENABLE = "enable"


class SetEnableCommand(JsonSetCommand, ABC):
    """Abstract set enable command."""

    _field_name = _ENABLE

    def __init_subclass__(cls, **kwargs: Any) -> None:
        cls._mqtt_params = MappingProxyType({cls._field_name: InitParam(bool, _ENABLE)})
        super().__init_subclass__(**kwargs)

    def __init__(self, enable: bool) -> None:
        super().__init__({self._field_name: 1 if enable else 0})
