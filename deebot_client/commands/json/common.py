"""Base commands."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from deebot_client.command import Command, CommandMqttP2P, CommandResult, InitParam
from deebot_client.const import DataType
from deebot_client.event_bus import EventBus
from deebot_client.events import AvailabilityEvent, EnableEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import (
    HandlingResult,
    HandlingState,
    MessageBody,
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


class CommandWithMessageHandling(JsonCommand, MessageBody, ABC):
    """Command, which handle response by itself."""

    _is_available_check: bool = False

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """
        if response.get("ret") == "ok":
            data = response.get("resp", response)
            result = self.handle(event_bus, data)
            return CommandResult(result.state, result.args)

        if errno := response.get("errno", None):
            match errno:
                case 4200:
                    # bot offline
                    _LOGGER.info(
                        'Vacuum is offline. Could not execute command "%s"', self.name
                    )
                    event_bus.notify(AvailabilityEvent(False))
                    return CommandResult(HandlingState.FAILED)
                case 500:
                    if self._is_available_check:
                        _LOGGER.info(
                            'No response received for command "%s" during availability-check.',
                            self.name,
                        )
                    else:
                        _LOGGER.warning(
                            'No response received for command "%s". This can happen if the vacuum has network issues or does not support the command',
                            self.name,
                        )
                    return CommandResult(HandlingState.FAILED)

        _LOGGER.warning('Command "%s" was not successfully.', self.name)
        return CommandResult(HandlingState.ANALYSE)


class ExecuteCommand(CommandWithMessageHandling, ABC):
    """Command, which is executing something (ex. Charge)."""

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        """Handle message->body and notify the correct event subscribers.

        :return: A message response
        """
        # Success event looks like { "code": 0, "msg": "ok" }
        if body.get(CODE, -1) == 0:
            return HandlingResult.success()

        _LOGGER.warning('Command "%s" was not successfully. body=%s', cls.name, body)
        return HandlingResult(HandlingState.FAILED)


class SetCommand(ExecuteCommand, CommandMqttP2P, ABC):
    """Base set command.

    Command needs to be linked to the "get" command, for handling (updating) the sensors.
    """

    @property
    @abstractmethod
    def get_command(self) -> type[CommandWithMessageHandling]:
        """Return the corresponding "get" command."""
        raise NotImplementedError

    def handle_mqtt_p2p(self, event_bus: EventBus, response: dict[str, Any]) -> None:
        """Handle response received over the mqtt channel "p2p"."""
        result = self.handle(event_bus, response)
        if result.state == HandlingState.SUCCESS and isinstance(self._args, dict):
            self.get_command.handle(event_bus, self._args)


class GetEnableCommand(CommandWithMessageHandling, MessageBodyDataDict, ABC):
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
        event: EnableEvent = cls.event_type(bool(data["enable"]))  # type: ignore
        event_bus.notify(event)
        return HandlingResult.success()


class SetEnableCommand(SetCommand, ABC):
    """Abstract set enable command."""

    _mqtt_params = {"enable": InitParam(bool)}

    def __init__(self, enable: bool) -> None:
        super().__init__({"enable": 1 if enable else 0})
