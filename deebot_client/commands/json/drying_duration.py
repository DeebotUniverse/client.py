"""Drying duration command module."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import DryingDuration, DryingDurationEvent
from deebot_client.message import HandlingResult
from deebot_client.util import get_enum

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetDryingDuration(JsonGetCommand):
    """Get the hot air drying duration command."""

    NAME = "getDryingDuration"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(DryingDurationEvent(DryingDuration(int(data["duration"]))))
        return HandlingResult.success()


class SetDryingDuration(JsonSetCommand):
    """Set the hot air drying duration command."""

    NAME = "setDryingDuration"
    get_command = GetDryingDuration
    _mqtt_params = MappingProxyType({"duration": InitParam(DryingDuration)})

    def __init__(self, duration: DryingDuration | str) -> None:
        if isinstance(duration, str):
            duration = get_enum(DryingDuration, duration)
        super().__init__({"duration": duration.value})
