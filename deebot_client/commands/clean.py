"""Clean commands."""
from enum import Enum, unique
from typing import Any
from xml.etree import ElementTree

from ..authentication import Authenticator
from ..command import CommandResult
from ..events import StateEvent
from ..logging_filter import get_logger
from ..message import HandlingResult, MessageBodyDataDict
from ..models import DeviceInfo, VacuumState
from .common import EventBus, ExecuteCommand, NoArgsCommand

_LOGGER = get_logger(__name__)


@unique
class CleanAction(str, Enum):
    """Enum class for all possible clean actions."""

    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"

    # Currently only used for the Deebot 900
    HALT = "halt"


@unique
class CleanMode(str, Enum):
    """Enum class for all possible clean modes."""

    AUTO = "auto"
    SPOT_AREA = "spotArea"
    CUSTOM_AREA = "customArea"


@unique
class CleanSpeed(str, Enum):
    """Enum class for all possible clean speeds.

    Currently only used for the Deebot 900.
    """

    STANDARD = "standard"
    STRONG = "strong"


class Clean(ExecuteCommand):
    """Clean command."""

    name = "clean"

    xml_name = "Clean"

    xml_has_own_element = True

    def __init__(self, action: CleanAction) -> None:
        super().__init__(self.__get_args(action))

    async def _execute(
        self, authenticator: Authenticator, device_info: DeviceInfo, event_bus: EventBus
    ) -> CommandResult:
        """Execute command."""
        state = event_bus.get_last_event(StateEvent)
        if state and isinstance(self._args, dict) and not device_info.uses_xml_protocol:
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

        if state and isinstance(self._args, dict) and device_info.uses_xml_protocol:
            if (
                self._args["act"] == CleanAction.RESUME.value
                and state.state != VacuumState.PAUSED
            ):
                self._args = str(self.__get_args(CleanAction.START))[0]
            elif (
                self._args["act"] == CleanAction.START.value
                and state.state == VacuumState.PAUSED
            ):
                self._args = str(self.__get_args(CleanAction.RESUME))[0]
            elif self._args["act"] == CleanAction.START.value:
                self._args["act"] = str(CleanAction.START.value)[0]

            elif self._args["act"] == CleanAction.STOP.value:
                self._args["act"] = str(CleanAction.HALT.value)[0]

            if "speed" not in self._args:
                self._args["speed"] = CleanSpeed.STANDARD.value

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
            raise ValueError("args must be a dict!")

        self._args["type"] = mode.value
        self._args["content"] = str(area)
        self._args["count"] = cleanings


class GetCleanInfo(NoArgsCommand, MessageBodyDataDict):
    """Get clean info command."""

    name = "getCleanInfo"

    xml_name = "GetCleanState"

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

    @classmethod
    def _handle_body_data_xml(cls, event_bus: EventBus, xml_message: str):
        status: VacuumState | None = None

        tree = ElementTree.fromstring(xml_message)
        element = tree.find("clean")
        raw_state = element.attrib.get("st")
        a = element.attrib.get("a")  # Action ?

        if raw_state == "h" and a == "1":
            status = VacuumState.IDLE
        elif raw_state == "p" and a == "0":
            status = VacuumState.PAUSED
        elif raw_state == "s" and a == "0":
            status = VacuumState.CLEANING
        elif raw_state == "h" and a == "0":
            status = VacuumState.RETURNING

        if status:
            event_bus.notify(StateEvent(status))
            return HandlingResult.success()

        return HandlingResult.analyse()
