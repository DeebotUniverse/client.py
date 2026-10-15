"""Clean info messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from deebot_client.events import StateEvent
from deebot_client.events.mower import MowingTaskEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import State

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)


class OnCleanInfo(MessageBodyDataDict):
    """On clean info message."""

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
        content: dict[str, Any] = {}
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
                area_values: Any = content
                if "value" in content:
                    area_values = content.get("value")

                _LOGGER.debug("Last custom area values (x1,y1,x2,y2): %s", area_values)

        elif state == "goCharging":
            status = State.RETURNING
        elif state == "idle":
            status = State.IDLE

        if status:
            event_bus.notify(StateEvent(status))
            if (mower := event_bus.capabilities.mower) and mower.task:
                cls._notify_mowing_task(event_bus, status, content)
            return HandlingResult.success()

        return HandlingResult.analyse()

    @classmethod
    def _notify_mowing_task(
        cls, event_bus: EventBus, status: State, content: dict[str, Any]
    ) -> None:
        if status in (State.CLEANING, State.PAUSED) and (task := content.get("type")):
            # border mowing reports the area as "aid:1"
            value = (content.get("value") or "").removeprefix("aid:")
            area_ids = [area for area in value.split(",") if area]
            event_bus.notify(
                MowingTaskEvent(type=task, area_ids=area_ids, scheduled=cls._SCHEDULED)
            )
        elif status == State.IDLE:
            # The task stays active while returning to the station and can be resumed
            event_bus.notify(MowingTaskEvent(type=None, area_ids=[]))

    _SCHEDULED: ClassVar[bool] = False


class OnScheduleTaskInfo(OnCleanInfo):
    """On schedule task info message.

    Send by mowers instead of onCleanInfo, while a scheduled task is running.
    """

    NAME = "onScheduleTaskInfo"
    _SCHEDULED = True
