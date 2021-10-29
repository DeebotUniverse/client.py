"""Clean commands."""
import logging
from enum import Enum, unique
from typing import Any, Dict, Optional

from ..events import StatusEventDto
from ..models import VacuumState
from .common import EventBus, _ExecuteCommand, _NoArgsCommand

_LOGGER = logging.getLogger(__name__)


@unique
class CleanAction(str, Enum):
    """Enum class for all possible clean actions."""

    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"


@unique
class CleanMode(str, Enum):
    """Enum class for all possible clean modes."""

    AUTO = "auto"
    SPOT_AREA = "spotArea"
    CUSTOM_AREA = "customArea"


class Clean(_ExecuteCommand):
    """Clean command."""

    name = "clean"

    def __init__(self, action: CleanAction) -> None:
        args = {"act": action.value}
        if action == CleanAction.START:
            args["type"] = CleanMode.AUTO.value
        super().__init__(args)


class CleanArea(Clean):
    """Clean area command."""

    def __init__(self, mode: CleanMode, area: str, cleanings: int = 1) -> None:
        super().__init__(CleanAction.START)
        if not isinstance(self.args, dict):
            raise ValueError("args must be a dict!")

        self.args["type"] = mode.value
        self.args["content"] = str(area)
        self.args["count"] = cleanings


class GetCleanInfo(_NoArgsCommand):
    """Get clean info command."""

    name = "getCleanInfo"

    @classmethod
    def _handle_body_data_dict(cls, event_bus: EventBus, data: Dict[str, Any]) -> bool:
        """Handle message->body->data and notify the correct event subscribers.

        :return: True if data was valid and no error was included
        """

        status: Optional[VacuumState] = None
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
            event_bus.notify(StatusEventDto(True, status))

        return True
