"""Custom command module."""
from typing import Any

from deebot_client.command import CommandResult
from deebot_client.commands.json.common import JsonCommand
from deebot_client.event_bus import EventBus
from deebot_client.events import CustomCommandEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingState

_LOGGER = get_logger(__name__)


class CustomCommand(JsonCommand):
    """Custom command, used when user wants to execute a command, which is not part of this library."""

    name: str = "CustomCommand"

    def __init__(
        self, name: str, args: dict[str, Any] | list[Any] | None = None
    ) -> None:
        self.name = name
        super().__init__(args)

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """
        if response.get("ret") == "ok":
            data = response.get("resp", response)
            event_bus.notify(CustomCommandEvent(self.name, data))
            return CommandResult.success()

        _LOGGER.warning('Command "%s" was not successfully: %s', self.name, response)
        return CommandResult(HandlingState.FAILED)

    def __eq__(self, obj: object) -> bool:
        if super().__eq__(obj) and isinstance(obj, CustomCommand):
            return self.name == obj.name

        return False

    def __hash__(self) -> int:
        return super().__hash__() + hash(self.name)


class CustomPayloadCommand(CustomCommand):
    """Custom command, where args is the raw payload."""

    def _get_json_payload(self) -> dict[str, Any] | list[Any]:
        return self._args
