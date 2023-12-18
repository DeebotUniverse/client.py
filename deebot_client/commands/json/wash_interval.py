"""Pads cleaning interval commands."""
from types import MappingProxyType
from typing import Any

from deebot_client.command import InitParam
from deebot_client.event_bus import EventBus
from deebot_client.events.wash_interval import WashIntervalEvent
from deebot_client.message import HandlingResult

from .common import JsonGetCommand, JsonSetCommand


class GetWashInterval(JsonGetCommand):
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


class SetWashInterval(JsonSetCommand):
    """Set pads cleaning interval command."""

    name = "setWashInterval"
    get_command = GetWashInterval
    _mqtt_params = {"interval": InitParam(int)}

    def __init__(self, interval: int) -> None:
        if interval <= 0:
            raise ValueError("'interval' must be positive")
        super().__init__({"interval": interval})
