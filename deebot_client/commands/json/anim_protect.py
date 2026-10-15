"""Animal protection commands."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events.mower import AnimalProtectionEvent
from deebot_client.message import HandlingResult

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


def _normalize_time(value: str) -> str:
    """Normalize the time to HH:MM. The device reports sometimes "8:0"."""
    hours, minutes = value.split(":")
    return f"{int(hours):02d}:{int(minutes):02d}"


def _device_time(value: str) -> str:
    """Convert the time to the format used by the app ("8:0")."""
    hours, minutes = value.split(":")
    return f"{int(hours)}:{int(minutes)}"


class GetAnimProtect(JsonGetCommand):
    """Get animal protection command."""

    NAME = "getAnimProtect"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(
            AnimalProtectionEvent(
                enabled=bool(data["enable"]),
                start=_normalize_time(data["start"]),
                end=_normalize_time(data["end"]),
            )
        )
        return HandlingResult.success()


class SetAnimProtect(JsonSetCommand):
    """Set animal protection command."""

    NAME = "setAnimProtect"
    get_command = GetAnimProtect
    _mqtt_params = MappingProxyType(
        {
            "enable": InitParam(bool, "enabled"),
            "start": InitParam(str),
            "end": InitParam(str),
        }
    )

    def __init__(self, enabled: bool, start: str, end: str) -> None:
        super().__init__(
            {
                "enable": 1 if enabled else 0,
                "start": _device_time(start),
                "end": _device_time(end),
            }
        )
