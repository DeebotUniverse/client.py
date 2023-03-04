"""Base commands."""
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from ..command import Command, CommandResult
from ..events import EnableEvent
from ..events.event_bus import EventBus
from ..logging_filter import get_logger
from ..message import HandlingResult, HandlingState, Message, MessageBodyDataDict
from .const import CODE

_LOGGER = get_logger(__name__)


class CommandWithMessageHandling(Command, Message, ABC):
    """Command, which handle response by itself."""

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

        _LOGGER.warning('Command "%s" was not successfully: %s', self.name, response)
        return CommandResult(HandlingState.FAILED)


class CommandHandlingMqttP2P(CommandWithMessageHandling, ABC):
    """Command which handles also mqtt p2p messages."""

    @abstractmethod
    def handle_mqtt_p2p(self, event_bus: EventBus, response: dict[str, Any]) -> None:
        """Handle response received over the mqtt channel "p2p"."""


class NoArgsCommand(CommandWithMessageHandling, ABC):
    """Command without args."""

    def __init__(self) -> None:
        super().__init__()


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


class SetCommand(ExecuteCommand, CommandHandlingMqttP2P, ABC):
    """Base set command.

    Command needs to be linked to the "get" command, for handling (updating) the sensors.
    """

    def __init__(
        self,
        args: dict | list | None,
        **kwargs: Mapping[str, Any],
    ) -> None:
        if kwargs:
            _LOGGER.debug("Following passed parameters will be ignored: %s", kwargs)

        super().__init__(args)

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


class GetEnableCommand(NoArgsCommand, MessageBodyDataDict, ABC):
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

    def __init__(self, enable: int | bool, **kwargs: Mapping[str, Any]) -> None:
        if isinstance(enable, bool):
            enable = 1 if enable else 0
        super().__init__({"enable": enable}, **kwargs)
