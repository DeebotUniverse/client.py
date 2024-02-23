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

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        ota_event = OtaEvent(
            support_auto=bool(data.get("supportAuto", False)),
            auto_enabled=bool(data.get("autoSwitch", False)),
            version=data["ver"],
            status=data["status"],
            progress=data["progress"],
        )
        event_bus.notify(ota_event)
        return HandlingResult.success()

    @classmethod
    def handle_set_args(
        cls, event_bus: EventBus, args: dict[str, Any]
    ) -> HandlingResult:
        """Handle arguments of set command."""
        event_bus.notify(OtaEvent(support_auto=True, auto_enabled=args["autoSwitch"]))
        return HandlingResult.success()


class SetOta(JsonSetCommand):
    """Set ota command."""

    name = "setOta"
    get_command = GetOta

    _mqtt_params = MappingProxyType(
        {"autoSwitch": InitParam(bool, name="auto_enabled")}
    )

    def __init__(self, auto_enabled: bool) -> None:  # noqa: FBT001
        super().__init__({"autoSwitch": 1 if auto_enabled else 0})
