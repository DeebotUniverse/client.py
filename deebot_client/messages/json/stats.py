"""Stats messages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from deebot_client.events import (
    CleanJobStatus,
    Event,
    ReportStatsEvent,
    StatsEvent,
)
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


@dataclass(frozen=True)
class _CleanDataStatusEvent(Event):
    """Internal clean data status event."""

    finished: bool


class ReportStats(MessageBodyDataDict):
    """Report stats message."""

    NAME = "reportStats"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        status = CleanJobStatus.CLEANING
        if "stop" not in data:
            status = CleanJobStatus.NO_STATUS
        elif data["stop"] != 0:
            status = CleanJobStatus(int(data["stopReason"]))

        stats_event = ReportStatsEvent(
            area=data.get("area"),
            time=data.get("time"),
            type=data.get("type"),
            cleaning_id=data["cid"],
            status=status,
            content=[int(float(x)) for x in data.get("content", "").split(",") if x],
        )
        event_bus.notify(stats_event)
        return HandlingResult.success()


class OnCleanDataUpdateV2(MessageBodyDataDict):
    """Clean data update V2 message."""

    NAME = "onCleanDataUpdate_V2"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Track whether the current cleaning job completed normally."""
        for item in data.get("content", []):
            if isinstance(item, dict) and item.get("id") == 0:
                event_bus.notify(_CleanDataStatusEvent(item.get("status") == 3))
                break

        return HandlingResult.success()


class OnLastTimeStats(MessageBodyDataDict):
    """Last cleaning stats message."""

    NAME = "onLastTimeStats"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Report the final stats for a cleaning job."""
        clean_data_status = event_bus.get_last_event(_CleanDataStatusEvent)
        status = (
            CleanJobStatus.FINISHED
            if clean_data_status and clean_data_status.finished
            else CleanJobStatus.MANUALLY_STOPPED
        )

        event_bus.notify(
            ReportStatsEvent(
                area=data.get("area"),
                time=data.get("time"),
                type=data.get("type"),
                cleaning_id=data.get("start", ""),
                status=status,
                content=[],
            )
        )
        return HandlingResult.success()


class OnStats(MessageBodyDataDict):
    """Get stats command."""

    NAME = "onStats"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(
            StatsEvent(area=data["area"], time=data["time"], type=data.get("type"))
        )
        return HandlingResult.success()
