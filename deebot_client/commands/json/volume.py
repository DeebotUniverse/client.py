"""Volume command module."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import FallVolumeEvent, VolumeEvent
from deebot_client.message import HandlingResult

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetVolume(JsonGetCommand):
    """Get volume command."""

    NAME = "getVolume"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if data.get("type") == "fall":
            event_bus.notify(
                FallVolumeEvent(volume=data["volume"], maximum=data.get("total"))
            )
            return HandlingResult.success()

        event_bus.notify(VolumeEvent(volume=data["volume"], maximum=data.get("total")))
        if "fallVolume" in data:
            event_bus.notify(
                FallVolumeEvent(volume=data["fallVolume"], maximum=data.get("total"))
            )
        return HandlingResult.success()


class SetVolume(JsonSetCommand):
    """Set volume command."""

    NAME = "setVolume"
    get_command = GetVolume
    _mqtt_params = MappingProxyType(
        {
            "volume": InitParam(int),
            "type": InitParam(str, "channel", optional=True),
            "total": InitParam(int, optional=True),
        }
    )

    def __init__(
        self, volume: int, channel: str | None = None, total: int | None = None
    ) -> None:
        args: dict[str, Any] = {"volume": volume}
        if channel is not None:
            args["type"] = channel
        if total is not None:
            args["total"] = total
        super().__init__(args)


class SetFallVolume(JsonSetCommand):
    """Set lifted-alarm volume."""

    NAME = "setVolume"
    get_command = GetVolume
    _mqtt_params = MappingProxyType(
        {
            "volume": InitParam(int),
            "type": None,
            "total": InitParam(int, optional=True),
        }
    )

    def __init__(self, volume: int, total: int = 10) -> None:
        super().__init__({"type": "fall", "total": total, "volume": volume})
