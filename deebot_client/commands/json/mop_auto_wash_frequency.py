"""Mop Auto-Wash Frequency command module."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import MopAutoWashFrequency, MopAutoWashFrequencyEvent
from deebot_client.message import HandlingResult
from deebot_client.util import get_enum

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetMopAutoWashFrequency(JsonGetCommand):
    """Get Mop Auto-Wash Frequency command."""

    name = "getWashInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.
        :return: A message response
        """
        event_bus.notify(MopAutoWashFrequencyEvent(MopAutoWashFrequency(int(data["interval"]))))
        return HandlingResult.success()


class SetMopAutoWashFrequency(JsonSetCommand):
    """Set Mop Auto-Wash Frequency command."""

    name = "setWashInfo"
    get_command = GetMopAutoWashFrequency
    _mqtt_params = MappingProxyType({"interval": InitParam(MopAutoWashFrequency)})

    def __init__(self, interval: MopAutoWashFrequency | int) -> None:
        if isinstance(interval, int):
            interval = get_enum(MopAutoWashFrequency, interval)
        super().__init__({"interval": interval.value})