"""Custom command module."""
import logging
from typing import Any, Dict, List, Union

from ..events import CustomCommandEvent
from ..message import HandlingState
from .common import CommandResult, EventBus

_LOGGER = logging.getLogger(__name__)


class CustomCommand:
    """Custom command, used when user wants to execute a command, which is not part of this library."""

    def __init__(self, name: str, args: Union[Dict, List, None] = None) -> None:
        self._name = name
        if args is None:
            args = {}
        self._args = args

    @property
    def name(self) -> str:
        """Command name."""
        return self._name

    @property
    def args(self) -> Union[Dict[str, Any], List]:
        """Command additional arguments."""
        return self._args

    def handle_requested(
        self, events: EventBus, response: Dict[str, Any]
    ) -> CommandResult:
        """Handle response from a manual requested command.

        :return: A message response
        """
        if response.get("ret") == "ok":
            data = response.get("resp", response)
            events.notify(CustomCommandEvent(self.name, data))
            return CommandResult.success()

        _LOGGER.warning('Command "%s" was not successfully: %s', self.name, response)
        return CommandResult(HandlingState.FAILED)
