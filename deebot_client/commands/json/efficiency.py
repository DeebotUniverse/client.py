"""Efficiency mode command module."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import EfficiencyMode, EfficiencyModeEvent
from deebot_client.message import HandlingResult
from deebot_client.util import get_enum

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetEfficiencyMode(JsonGetCommand):
    """Get efficiency mode command."""

    NAME = "getEfficiency"

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

    NAME = "setEfficiency"
    get_command = GetEfficiencyMode
    _mqtt_params = MappingProxyType({"efficiency": InitParam(EfficiencyMode)})

    def __init__(self, efficiency: EfficiencyMode | str) -> None:
        if isinstance(efficiency, str):
            efficiency = get_enum(EfficiencyMode, efficiency)
        super().__init__({"efficiency": efficiency.value})
