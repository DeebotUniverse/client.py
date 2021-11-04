"""Base commands."""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Mapping, Type, Union

from ..command import Command
from ..events.event_bus import EventBus
from ..message import Message, MessageHandling, MessageResponse

_LOGGER = logging.getLogger(__name__)

_CODE = "code"


class CommandWithHandling(Command, Message, ABC):
    """Command, which handle response by itself."""

    # required as name is class variable, will be overwritten in subclasses
    name = "__invalid__"

    def handle_requested(
        self, event_bus: EventBus, response: Dict[str, Any]
    ) -> MessageResponse:
        """Handle response from a manual requested command.

        :return: A message response
        """
        if response.get("ret") == "ok":
            data = response.get("resp", response)
            return self.handle(event_bus, data)

        _LOGGER.warning('Command "%s" was not successfully: %s', self.name, response)
        return MessageResponse(MessageHandling.FAILED)


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
    def _handle_body(cls, event_bus: EventBus, body: Dict[str, Any]) -> MessageResponse:
        """Handle message->body and notify the correct event subscribers.

        :return: A message response
        """
        # Success event looks like { "code": 0, "msg": "ok" }
        if body.get(_CODE, -1) == 0:
            return MessageResponse.success()

        _LOGGER.warning('Command "%s" was not successfully. body=%s', cls.name, body)
        return MessageResponse(MessageHandling.FAILED)


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
