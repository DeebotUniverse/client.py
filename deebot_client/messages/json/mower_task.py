"""Mower task messages (GOAT RTK models).

The end of a task is reported by the telemetry messages
"onFwBuryPoint-bd_task-mow-<type>-stop", which contain the real mowed area and time.
"onLastTimeStats" contains only the planned values.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import CleanJobStatus, ReportStatsEvent
from deebot_client.message import HandlingResult, MessageBody

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_TRIGGER_TO_STATUS = {
    "workComplete": CleanJobStatus.FINISHED,
    "app": CleanJobStatus.MANUALLY_STOPPED,
}


class _OnMowTaskStop(MessageBody):
    """On mow task stop message."""

    NAME = "onFwBuryPoint-bd_task-mow-stop"
    _TYPE: str

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        """Handle message->body and notify the correct event subscribers.

        Example: {"jobId": "540...", "mowedArea": 1.6525, "time": 151.55,
                  "trigger": "app", "workArea": 105.73, "workType": 2, ...}

        :return: A message response
        """
        status = _TRIGGER_TO_STATUS.get(
            str(body.get("trigger")), CleanJobStatus.FINISHED_WITH_WARNINGS
        )
        event_bus.notify(
            ReportStatsEvent(
                # mower areas are reported in cm²
                area=round(float(body.get("mowedArea", 0)) * 10000),
                time=round(float(body.get("time", 0))),
                type=cls._TYPE,
                cleaning_id=str(body.get("jobId", "")),
                status=status,
                content=[],
            )
        )
        return HandlingResult.success()


class OnMowAutoTaskStop(_OnMowTaskStop):
    """On auto mowing stop message."""

    NAME = "onFwBuryPoint-bd_task-mow-auto-stop"
    _TYPE = "auto"


class OnMowAreaTaskStop(_OnMowTaskStop):
    """On area mowing stop message."""

    NAME = "onFwBuryPoint-bd_task-mow-spotarea-stop"
    _TYPE = "spotArea"


class OnMowBorderTaskStop(_OnMowTaskStop):
    """On edge mowing stop message."""

    NAME = "onFwBuryPoint-bd_task-mow-border-stop"
    _TYPE = "border"


class OnMowScheduleTaskStop(_OnMowTaskStop):
    """On scheduled mowing stop message."""

    NAME = "onFwBuryPoint-bd_task-mow-schedule-stop"
    _TYPE = "schedule"
