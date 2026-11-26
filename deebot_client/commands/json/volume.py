"""Volume command module."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import VolumeEvent
from deebot_client.message import HandlingResult, HandlingState

from .common import ExecuteCommand, JsonGetCommand, JsonSetCommand, NgiotJsonCommand

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
        event_bus.notify(VolumeEvent(volume=data["volume"], maximum=data.get("total")))
        return HandlingResult.success()


class SetVolume(JsonSetCommand):
    """Set volume command."""

    NAME = "setVolume"
    get_command = GetVolume
    _mqtt_params = MappingProxyType(
        {
            "volume": InitParam(int),
            "total": None,  # Remove it as we don't can set it (App includes it)
        }
    )

    def __init__(self, volume: int) -> None:
        super().__init__({"volume": volume})


# The eyfj07 app captures show discrete volume levels from zero to five.
_NGIOT_MAX_VOLUME = 5


class NgiotGetVolume(NgiotJsonCommand, GetVolume):
    """Get speaker volume through NGIOT."""

    NAME = "ngiotGetVolume"
    APN = "10001"

    def __init__(self) -> None:
        super().__init__({"fields": ["volume"]})

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        volume = data.get("volume")
        if (
            not isinstance(volume, int)
            or isinstance(volume, bool)
            or not 0 <= volume <= _NGIOT_MAX_VOLUME
        ):
            return HandlingResult.analyse()

        return super()._handle_body_data_dict(
            event_bus, {"volume": volume, "total": _NGIOT_MAX_VOLUME}
        )


class NgiotSetVolume(NgiotJsonCommand, ExecuteCommand):
    """Set speaker volume through NGIOT and request the updated state."""

    NAME = "ngiotSetVolume"
    APN = "50023"

    def __init__(self, volume: int) -> None:
        if (
            not isinstance(volume, int)
            or isinstance(volume, bool)
            or not 0 <= volume <= _NGIOT_MAX_VOLUME
        ):
            msg = f"Volume must be an integer between 0 and {_NGIOT_MAX_VOLUME}"
            raise ValueError(msg)
        super().__init__({"volume": volume})

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        result = super()._handle_body(event_bus, body)
        if result.state == HandlingState.SUCCESS:
            return HandlingResult(result.state, requested_commands=[NgiotGetVolume()])
        return result
