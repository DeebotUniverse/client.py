"""Efficiency mode command module."""
from typing import Any

from deebot_client.command import InitParam
from deebot_client.event_bus import EventBus
from deebot_client.events import EfficiencyMode, EfficiencyModeEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import JsonCommandWithMessageHandling, JsonSetCommand


class GetEfficiencyMode(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get efficiency mode command."""

    name = "getEfficiency"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(EfficiencyModeEvent(EfficiencyMode(int(data["efficiency"]))))
        return HandlingResult.success()


class SetEfficiencyMode(JsonSetCommand):
    """Set efficiency mode command."""

    name = "setEfficiency"
    get_command = GetEfficiencyMode
    _mqtt_params = {"efficiency": InitParam(EfficiencyMode)}

    def __init__(self, mode: EfficiencyMode | str) -> None:
        if isinstance(mode, str):
            mode = EfficiencyMode.get(mode)
        super().__init__({"efficiency": mode.value})
