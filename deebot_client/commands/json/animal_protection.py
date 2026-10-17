"""Animal protection commands."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import AnimalProtectionEvent
from deebot_client.message import HandlingResult

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


def normalize_time(value: str) -> str:
    """Normalize device times to zero-padded HH:MM."""
    hour, minute = value.split(":", maxsplit=1)
    return f"{hour.zfill(2)}:{minute.zfill(2)}"


class GetAnimalProtection(JsonGetCommand):
    """Get animal protection configuration."""

    NAME = "getAnimProtect"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        event_bus.notify(
            AnimalProtectionEvent(
                enabled=bool(data["enable"]),
                start=normalize_time(data["start"]),
                end=normalize_time(data["end"]),
            )
        )
        return HandlingResult.success()


class SetAnimalProtection(JsonSetCommand):
    """Set the complete animal protection configuration."""

    NAME = "setAnimProtect"
    get_command = GetAnimalProtection
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
                "start": normalize_time(start),
                "end": normalize_time(end),
            }
        )
