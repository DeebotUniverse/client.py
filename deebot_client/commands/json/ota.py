"""Ota command module."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import OtaEvent
from deebot_client.message import HandlingResult
from deebot_client.messages.json.ota import OnOta

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetOta(OnOta, JsonGetCommand):
    """Get ota command."""

    NAME = "getOta"

    @classmethod
    def handle_set_args(
        cls, event_bus: EventBus, args: dict[str, Any]
    ) -> HandlingResult:
        """Handle arguments of set command."""
        event_bus.notify(OtaEvent(support_auto=True, auto_enabled=args["autoSwitch"]))
        return HandlingResult.success()


class SetOta(JsonSetCommand):
    """Set ota command."""

    NAME = "setOta"
    get_command = GetOta

    _mqtt_params = MappingProxyType({"autoSwitch": InitParam(bool, "auto_enabled")})

    def __init__(self, auto_enabled: bool) -> None:
        super().__init__({"autoSwitch": 1 if auto_enabled else 0})
