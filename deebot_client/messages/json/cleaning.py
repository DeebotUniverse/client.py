"""X2 room progress and final statistics messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.cleaning import (
    LastCleaningStatsEvent,
    RoomProgress,
    RoomProgressEvent,
)
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnCleanDataUpdateV2(MessageBodyDataDict):
    """Preserve room status codes without assuming their meaning."""

    NAME = "onCleanDataUpdate_V2"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Parse a notification without inferring its stop reason."""
        try:
            rooms = tuple(
                RoomProgress(
                    room_id=int(r["id"]), status=int(r["status"]), type=int(r["type"])
                )
                for r in data["content"]
            )
            event = RoomProgressEvent(
                str(data["cid"]), str(data["mid"]), str(data["type"]), rooms
            )
        except KeyError, TypeError, ValueError:
            return HandlingResult.analyse()
        event_bus.notify(event)
        return HandlingResult.success()


class OnLastTimeStats(MessageBodyDataDict):
    """Final statistics are not a success or stop-reason notification."""

    NAME = "onLastTimeStats"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Parse a notification without inferring its stop reason."""
        try:
            start, area, time = (int(data[key]) for key in ("start", "area", "time"))
            if min(start, area, time) < 0:
                return HandlingResult.analyse()
            event = LastCleaningStatsEvent(start, area, time, str(data["type"]))
        except KeyError, TypeError, ValueError:
            return HandlingResult.analyse()
        event_bus.notify(event)
        return HandlingResult.success()
