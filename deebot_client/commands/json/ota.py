"""Ota command module."""
from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import OtaEvent
from deebot_client.message import HandlingResult

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetOta(JsonGetCommand):
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


class SetOta(JsonSetCommand):
    """Set ota command."""

    name = "setOta"
    get_command = GetOta

    _mqtt_params = MappingProxyType({"autoSwitch": InitParam(bool, "enable")})

    def __init__(self, enable: bool) -> None:  # noqa: FBT001
        super().__init__({"autoSwitch": 1 if enable else 0})
