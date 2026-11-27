"""Wash info messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.mop_auto_wash_frequency import MopAutoWashFrequencyEvent
from deebot_client.events.wash_info import (
    MopAutoWashMode,
    MopAutoWashModeEvent,
    MopWashMode,
    MopWashModeEvent,
)
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)


class OnWashInfo(MessageBodyDataDict):
    """On wash info message.

    The robot reports all fields, but set commands (and the app) may only
    contain some of them, so every field is optional.
    """

    NAME = "onWashInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if (interval := data.get("interval")) is not None:
            event_bus.notify(MopAutoWashFrequencyEvent(int(interval)))

        if (mode := data.get("mode")) is not None:
            try:
                event_bus.notify(MopWashModeEvent(MopWashMode(int(mode))))
            except ValueError:
                _LOGGER.debug("Unknown mop wash mode: %s", mode)

        if (wise_mode := data.get("wiseMode")) is not None:
            try:
                event_bus.notify(MopAutoWashModeEvent(MopAutoWashMode(int(wise_mode))))
            except ValueError:
                _LOGGER.debug("Unknown mop auto-wash mode: %s", wise_mode)

        return HandlingResult.success()
