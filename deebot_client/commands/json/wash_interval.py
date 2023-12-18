"""Pads cleaning interval commands."""
from typing import Any

from deebot_client.command import InitParam
from deebot_client.event_bus import EventBus
from deebot_client.events.pads_cleaning_interval import PadsCleaningIntervalEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import CommandWithMessageHandling, SetCommand


class GetWashInterval(CommandWithMessageHandling, MessageBodyDataDict):
    """Get pads cleaning interval command."""

    name = "getWashInterval"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(WashIntervalEvent(int(data["interval"])))
        return HandlingResult.success()


class SeWashInterval(SetCommand):
    """Set pads cleaning interval command."""

    name = "setWashInterval"
    get_command = GetWashInterval
    _mqtt_params = {"interval": InitParam(int)}

    def __init__(self, interval: int) -> None:
        if interval <= 0:
            raise ValueError("'interval' must be positive")
        super().__init__({"interval": interval})
