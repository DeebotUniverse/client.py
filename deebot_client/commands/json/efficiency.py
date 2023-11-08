"""Clean count command module."""


from typing import Any

from deebot_client.command import InitParam
from deebot_client.event_bus import EventBus
from deebot_client.events import EfficiencyModeEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import CommandWithMessageHandling, SetCommand


class GetEfficiencyMode(CommandWithMessageHandling, MessageBodyDataDict):
    """Get efficiency mode command."""

    name = "getEfficiency"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """

        event_bus.notify(EfficiencyModeEvent(efficiency=data["efficiency"]))
        return HandlingResult.success()


class SetEfficiencyMode(SetCommand):
    """Set efficiency mode command."""

    name = "setEfficiency"
    get_command = GetEfficiencyMode
    _mqtt_params = {"efficiency": InitParam(bool)}

    def __init__(self, efficiency: bool) -> None:
        super().__init__({"efficiency": 1 if efficiency else 0})
