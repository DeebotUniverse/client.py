"""Clean commands."""
from enum import Enum, unique
from typing import Any
from xml.etree import ElementTree

from deebot_client.authentication import Authenticator
from deebot_client.command import CommandResult
from deebot_client.events import StateEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import DeviceInfo, VacuumState

from .common import EventBus, ExecuteCommand, NoArgsCommand

_LOGGER = get_logger(__name__)


# TODO, move to a generic directory?
@unique
class CleanAction(str, Enum):
    """Enum class for all possible clean actions."""

    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"

    # Currently only used for the Deebot 900
    HALT = "halt"


# TODO, move to a generic directory?
@unique
class CleanMode(str, Enum):
    """Enum class for all possible clean modes."""

    AUTO = "auto"
    SPOT_AREA = "spotArea"
    CUSTOM_AREA = "customArea"


class Clean(ExecuteCommand):
    """Clean command."""

    name = "clean"

    def __init__(self, action: CleanAction) -> None:
        super().__init__(self.__get_args(action))

    async def _execute(
        self, authenticator: Authenticator, event_bus: EventBus
    ) -> CommandResult:
        """Execute command."""
        state = event_bus.get_last_event(StateEvent)

        if state and isinstance(self._args, dict) :
            if (
                self._args["act"] == CleanAction.RESUME.value
                and state.state != VacuumState.PAUSED
            ):
                self._args = self.__get_args(CleanAction.START)
            elif (
                self._args["act"] == CleanAction.START.value
                and state.state == VacuumState.PAUSED
            ):
                self._args = self.__get_args(CleanAction.RESUME)

        return await super()._execute(authenticator, event_bus)

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
            raise ValueError("args must be a dict!")

        self._args["type"] = mode.value
        self._args["content"] = str(area)
        self._args["count"] = cleanings


class GetCleanInfo(NoArgsCommand, MessageBodyDataDict):
    """Get clean info command."""

    name = "getCleanInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """

        status: VacuumState | None = None
        state = data.get("state")
        if data.get("trigger") == "alert":
            status = VacuumState.ERROR
        elif state == "clean":
            clean_state = data.get("cleanState", {})
            motion_state = clean_state.get("motionState")
            if motion_state == "working":
                status = VacuumState.CLEANING
            elif motion_state == "pause":
                status = VacuumState.PAUSED
            elif motion_state == "goCharging":
                status = VacuumState.RETURNING

            clean_type = clean_state.get("type")
            content = clean_state.get("content", {})
            if "type" in content:
                clean_type = content.get("type")

            if clean_type == "customArea":
                area_values = content
                if "value" in content:
                    area_values = content.get("value")

                _LOGGER.debug("Last custom area values (x1,y1,x2,y2): %s", area_values)

        elif state == "goCharging":
            status = VacuumState.RETURNING
        elif state == "idle":
            status = VacuumState.IDLE

        if status:
            event_bus.notify(StateEvent(status))
            return HandlingResult.success()

        return HandlingResult.analyse()
