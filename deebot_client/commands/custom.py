"""Custom command module."""
from typing import Any

from ..command import Command, CommandResult, EventBus
from ..events import CustomCommandEvent
from ..logging_filter import get_logger
from ..message import HandlingState

_LOGGER = get_logger(__name__)


class CustomCommand(Command):
    """Custom command, used when user wants to execute a command, which is not part of this library."""

    name = "CustomCommand"

    def __init__(self, name: str, args: dict | list | None = None) -> None:
        self._name = name
        super().__init__(args)

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """
        if response.get("ret") == "ok":
            data = response.get("resp", response)
            event_bus.notify(CustomCommandEvent(self._name, data))
            return CommandResult.success()

        _LOGGER.warning('Command "%s" was not successfully: %s', self._name, response)
        return CommandResult(HandlingState.FAILED)

    def __eq__(self, obj: object) -> bool:
        if super().__eq__(obj) and isinstance(obj, CustomCommand):
            return self._name == obj._name

        return False

    def __hash__(self) -> int:
        return super().__hash__() + hash(self._name)
