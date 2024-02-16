"""Clean messages."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import StateEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import State

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)


class OnCleanInfo(MessageBodyDataDict):
    """Clean info message."""

    name = "onCleanInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        status: State | None = None
        state = data.get("state")
        trigger = data.get("trigger")
        clean_state = data.get("cleanState", {})
        motion_state = clean_state.get("motionState")
        content = clean_state.get("content", {})
        clean_type = clean_state.get("type")

        match trigger, state, motion_state:
            case "alert", _, _:
                status = State.ERROR
            case _, "clean", "working":
                status = State.CLEANING
            case _, "clean", "pause":
                status = State.PAUSED
            case _, "clean", "goCharging":
                status = State.RETURNING
            case _, "goCharging", _:
                status = State.RETURNING
            case _, "idle", _:
                status = State.IDLE

        if clean_type == "customArea":
            area_values = content if "value" in content else content.get("value")
            _LOGGER.debug("Last custom area values (x1,y1,x2,y2): %s", area_values)

        if status is not None:
            event_bus.notify(StateEvent(status))
            return HandlingResult.success()

        return HandlingResult.analyse()


class OnCleanInfoV2(OnCleanInfo):
    """Clean info v2 message."""

    name = "onCleanInfo_V2"
