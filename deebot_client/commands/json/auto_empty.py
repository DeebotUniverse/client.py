"""Auto empty command module."""
from typing import Any

from deebot_client.command import InitParam
from deebot_client.event_bus import EventBus
from deebot_client.events import AutoEmptyMode, AutoEmptyModeEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import JsonCommandWithMessageHandling, JsonSetCommand


class GetAutoEmpty(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get auto empty command."""

    name = "getAutoEmpty"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(
            AutoEmptyModeEvent(
                enable=bool(data["enable"]),
                mode=AutoEmptyMode(str(data["frequency"])),
            )
        )
        return HandlingResult.success()


class SetAutoEmpty(JsonSetCommand):
    """Set auto empty command."""

    name = "setAutoEmpty"
    get_command = GetAutoEmpty
    _mqtt_params = {"enable": InitParam(bool), "frequency": InitParam(AutoEmptyMode)}

    def __init__(
        self, enable: bool = True, frequency: AutoEmptyMode | str | None = None
    ) -> None:
        args: dict[str, int | str] = {"enable": int(enable)}
        if frequency is not None:
            if isinstance(frequency, str):
                frequency = AutoEmptyMode.get(frequency)
            args["frequency"] = frequency.value

        super().__init__(args)
