"""Base commands."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Type, Union

from ..command import Command
from ..events import EnableEvent
from ..events.event_bus import EventBus
from ..logging_filter import get_logger
from ..message import HandlingResult, HandlingState, Message

_LOGGER = get_logger(__name__)

_CODE = "code"


@dataclass(frozen=True)
class CommandResult(HandlingResult):
    """Command result object."""

    requested_commands: Optional[List[Command]] = None

    @classmethod
    def success(cls) -> "CommandResult":
        """Create result with handling success."""
        return CommandResult(HandlingState.SUCCESS)

    @classmethod
    def analyse(cls) -> "CommandResult":
        """Create result with handling analyse."""
        return CommandResult(HandlingState.ANALYSE)


class CommandWithHandling(Command, Message, ABC):
    """Command, which handle response by itself."""

    # required as name is class variable, will be overwritten in subclasses
    name = "__invalid__"

    def handle_requested(
        self, event_bus: EventBus, response: Dict[str, Any]
    ) -> CommandResult:
        """Handle response from a manual requested command.

        :return: A message response
        """
        if response.get("ret") == "ok":
            data = response.get("resp", response)
            result = self.handle(event_bus, data)
            return CommandResult(result.state, result.args)

        _LOGGER.warning('Command "%s" was not successfully: %s', self.name, response)
        return CommandResult(HandlingState.FAILED)

    def handle_mqtt_p2p(self, event_bus: EventBus, response: Dict[str, Any]) -> None:
        """Handle response received over the mqtt channel "p2p"."""
        # Does nothing. Command will override this method.


class _NoArgsCommand(CommandWithHandling, ABC):
    """Command without args."""

    # required as name is class variable, will be overwritten in subclasses
    name = "__invalid__"

    def __init__(self) -> None:
        super().__init__()


class _ExecuteCommand(CommandWithHandling, ABC):
    """Command, which is executing something (ex. Charge)."""

    # required as name is class variable, will be overwritten in subclasses
    name = "__invalid__"

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: Dict[str, Any]) -> HandlingResult:
        """Handle message->body and notify the correct event subscribers.

        :return: A message response
        """
        # Success event looks like { "code": 0, "msg": "ok" }
        if body.get(_CODE, -1) == 0:
            return HandlingResult.success()

        _LOGGER.warning('Command "%s" was not successfully. body=%s', cls.name, body)
        return HandlingResult(HandlingState.FAILED)


class SetCommand(_ExecuteCommand, ABC):
    """Base set command.

    Command needs to be linked to the "get" command, for handling (updating) the sensors.
    """

    # required as name is class variable, will be overwritten in subclasses
    name = "__invalid__"

    def __init__(
        self,
        args: Union[Dict, List, None],
        **kwargs: Mapping[str, Any],
    ) -> None:
        if kwargs:
            _LOGGER.debug("Following passed parameters will be ignored: %s", kwargs)

        super().__init__(args)

    @property
    @abstractmethod
    def get_command(self) -> Type[CommandWithHandling]:
        """Return the corresponding "get" command."""
        raise NotImplementedError

    def handle_mqtt_p2p(self, event_bus: EventBus, response: Dict[str, Any]) -> None:
        """Handle response received over the mqtt channel "p2p"."""
        result = self.handle(event_bus, response)
        if result.state == HandlingState.SUCCESS and isinstance(self.args, dict):
            self.get_command.handle(event_bus, self.args)


class _GetEnableCommand(_NoArgsCommand):
    """Abstract get enable command."""

    # required as name is class variable, will be overwritten in subclasses
    name = "__invalid__"

    @classmethod
    @property
    @abstractmethod
    def event_type(cls) -> Type[EnableEvent]:
        """Event type."""
        raise NotImplementedError

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: Dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event: EnableEvent = cls.event_type(bool(data["enable"]))  # type: ignore
        event_bus.notify(event)
        return HandlingResult.success()


class SetEnableCommand(SetCommand):
    """Abstract set enable command."""

    # required as name is class variable, will be overwritten in subclasses
    name = "__invalid__"

    def __init__(self, enable: Union[int, bool], **kwargs: Mapping[str, Any]) -> None:
        if isinstance(enable, bool):
            enable = 1 if enable else 0
        super().__init__({"enable": enable}, **kwargs)
