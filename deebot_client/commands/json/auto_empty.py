"""Auto empty command module."""


from typing import Any

from deebot_client.command import InitParam
from deebot_client.event_bus import EventBus
from deebot_client.events.auto_empty import AutoEmptyMode, AutoEmptyModeEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import CommandWithMessageHandling, SetCommand


class GetAutoEmpty(CommandWithMessageHandling, MessageBodyDataDict):
    """Get auto empty command."""

    name = "getAutoEmpty"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(AutoEmptyModeEvent(AutoEmptyMode(str(data["frequency"]))))
        return HandlingResult.success()


class SetAutoEmpty(SetCommand):
    """Set auto empty command."""

    name = "setAutoEmpty"
    get_command = GetAutoEmpty
    _mqtt_params = {"enable": InitParam(int), "frequency": InitParam(AutoEmptyMode)}

    def __init__(self, mode: AutoEmptyMode | str) -> None:
        if isinstance(mode, str):
            mode = AutoEmptyMode.get(mode)
        super().__init__({"enable": 1, "frequency": mode.value})
