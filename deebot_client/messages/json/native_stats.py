"""Native completed-task duration telemetry, without inferred job status."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.message import HandlingResult, MessageBody

from .native_telemetry import handle_clean_stats

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnNativeCleanInfo(MessageBody):
    """Native task-end analytics reports duration in seconds, not minutes."""

    NAME = "onFwBuryPoint-bd_task-cleanInfo-evt"

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        if not any(
            command.NAME == "10001"
            for command in event_bus.capabilities.stats.clean.get
        ):
            return HandlingResult.success()
        handle_clean_stats(
            event_bus, {"cleanTime": body.get("cleanTime")}, seconds_per_unit=1
        )
        return HandlingResult.success()
