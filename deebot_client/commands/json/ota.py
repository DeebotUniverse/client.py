"""Ota command module."""

from typing import Any

from deebot_client.command import InitParam
from deebot_client.event_bus import EventBus
from deebot_client.events import OtaEvent
from deebot_client.message import (
    HandlingResult,
    MessageBodyDataDict,
)

from .common import (
    CommandWithMessageHandling,
    SetCommand,
)


class GetOta(CommandWithMessageHandling, MessageBodyDataDict):
    """Get ota command."""

    name = "getOta"
    event_type = OtaEvent

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(cls.event_type(bool(data["autoSwitch"])))
        return HandlingResult.success()


class SetOta(SetCommand):
    """Set ota command."""

    name = "setOta"
    get_command = GetOta

    _mqtt_params = {"autoSwitch": InitParam(bool, "enable")}

    def __init__(self, enable: bool) -> None:
        super().__init__({"autoSwitch": 1 if enable else 0})
