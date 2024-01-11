"""SweepMode command module for "Mop-Only" option."""

from types import MappingProxyType
from typing import Any

from deebot_client.command import InitParam
from deebot_client.event_bus import EventBus
from deebot_client.events import SweepModeEvent
from deebot_client.message import HandlingResult

from .common import JsonGetCommand, JsonSetCommand


class GetSweepMode(JsonGetCommand):
    """GetSweepMode command."""

    name = "getSweepMode"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(SweepModeEvent(data["type"]))
        return HandlingResult.success()


class SetSweepMode(JsonSetCommand):
    """SetSweepMode command."""

    name = "setSweepMode"
    get_command = GetSweepMode
    _mqtt_params = MappingProxyType({"type": InitParam(bool)})

    def __init__(self, enabled: bool) -> None:  # noqa: FBT001
        super().__init__({"type": enabled})
