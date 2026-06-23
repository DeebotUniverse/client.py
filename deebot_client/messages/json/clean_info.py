"""Clean info messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import StateEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.models import State

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)


def handle_clean_info(event_bus: EventBus, data: dict[str, Any]) -> HandlingResult:
    """Parse a clean-info payload and notify the matching state event.

    Shared by ``getCleanInfo``/``onCleanInfo`` and ``onScheduleTaskInfo`` (the
    scheduled-mow message), which all carry the same payload shape, e.g.
    ``{"state":"clean","cleanState":{"motionState":"working"}}``.
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

    if status is not None:
        event_bus.notify(StateEvent(status))
        return HandlingResult.success()

    return HandlingResult.analyse()


class OnScheduleTaskInfo(MessageBodyDataDict):
    """On schedule task info message.

    Scheduled mows are reported via ``onScheduleTaskInfo`` which carries the
    same payload as ``onCleanInfo``, so the clean-info parsing is reused.
    """

    NAME = "onScheduleTaskInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        return handle_clean_info(event_bus, data)
