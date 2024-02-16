"""Clean commands."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import StateEvent
from deebot_client.logging_filter import get_logger
from deebot_client.messages.json import OnCleanInfo, OnCleanInfoV2
from deebot_client.models import CleanAction, CleanMode, DeviceInfo, State

from .common import ExecuteCommand, JsonCommandWithMessageHandling

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator
    from deebot_client.command import CommandResult
    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)


class Clean(ExecuteCommand):
    """Clean command."""

    name = "clean"

    def __init__(self, action: CleanAction) -> None:
        super().__init__(self.__get_args(action))

    async def _execute(
        self, authenticator: Authenticator, device_info: DeviceInfo, event_bus: EventBus
    ) -> CommandResult:
        """Execute command."""
        state = event_bus.get_last_event(StateEvent)

        if state and isinstance(self._args, dict):
            if (
                self._args["act"] == CleanAction.RESUME.value
                and state.state != State.PAUSED
            ):
                self._args = self.__get_args(CleanAction.START)
            elif (
                self._args["act"] == CleanAction.START.value
                and state.state == State.PAUSED
            ):
                self._args = self.__get_args(CleanAction.RESUME)

        return await super()._execute(authenticator, device_info, event_bus)

    @staticmethod
    def __get_args(action: CleanAction) -> dict[str, Any]:
        args = {"act": action.value}
        if action == CleanAction.START:
            args["type"] = CleanMode.AUTO.value
        return args


class CleanArea(Clean):
    """Clean area command."""

    def __init__(self, mode: CleanMode, area: str, cleanings: int = 1) -> None:
        super().__init__(CleanAction.START)
        if not isinstance(self._args, dict):
            raise TypeError("args must be a dict!")

        self._args["type"] = mode.value
        self._args["content"] = str(area)
        self._args["count"] = cleanings


class GetCleanInfo(JsonCommandWithMessageHandling, OnCleanInfo):
    """Get clean info command."""

    name = "getCleanInfo"


class GetCleanInfoV2(JsonCommandWithMessageHandling, OnCleanInfoV2):
    """Get clean info command."""

    name = "getCleanInfo_V2"
