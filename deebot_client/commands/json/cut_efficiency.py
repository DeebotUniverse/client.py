"""Cut efficiency commands."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events.mower import CutEfficiency, CutEfficiencyEvent
from deebot_client.message import HandlingResult
from deebot_client.util import get_enum

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetCutEfficiency(JsonGetCommand):
    """Get cut efficiency command."""

    NAME = "getCutEfficiency"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(CutEfficiencyEvent(CutEfficiency(int(data["level"]))))
        return HandlingResult.success()


class SetCutEfficiency(JsonSetCommand):
    """Set cut efficiency command."""

    NAME = "setCutEfficiency"
    get_command = GetCutEfficiency
    _mqtt_params = MappingProxyType({"level": InitParam(CutEfficiency, "efficiency")})

    def __init__(self, efficiency: CutEfficiency | str) -> None:
        if isinstance(efficiency, str):
            efficiency = get_enum(CutEfficiency, efficiency)
        super().__init__({"level": efficiency.value})
