"""Clean activity messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.capabilities import DeviceType
from deebot_client.events import StateEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import State

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)


class OnCleanInfo(MessageBodyDataDict):
    """Clean activity reported by the device."""

    NAME = "onCleanInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        status: State | None = None
        state = data.get("state")
        if data.get("trigger") == "alert":
            status = State.ERROR
        elif state in ("clean", "washing"):
            clean_state = data.get("cleanState", {})
            motion_state = clean_state.get("motionState")
            if motion_state == "working":
                status = State.CLEANING
            elif motion_state == "pause":
                status = State.PAUSED
            elif motion_state == "goCharging":
                status = State.RETURNING

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
            status = State.RETURNING
        elif state == "idle":
            status = State.IDLE

        if status:
            event_bus.notify(StateEvent(status))
            return HandlingResult.success()

        return HandlingResult.analyse()


class OnScheduleTaskInfo(OnCleanInfo):
    """Mower activity from a scheduled task."""

    NAME = "onScheduleTaskInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        if event_bus.capabilities.device_type is not DeviceType.MOWER:
            return HandlingResult.analyse()
        return super()._handle_body_data_dict(event_bus, data)
