"""Volume commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import VolumeEvent
from deebot_client.message import HandlingResult, HandlingState

from .common import NgiotExecuteCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus
    from deebot_client.models import ApiDeviceInfo
    from deebot_client.ngiot_client import NgiotClient


class SetVolume(NgiotExecuteCommand):
    """Set device voice volume."""

    NAME = "setVolume"
    APN = "50023"
    MIN_VOLUME = 0
    MAX_VOLUME = 10

    def __init__(self, volume: int) -> None:
        super().__init__({})
        self._volume = int(volume)

    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, Any]:
        if not self.MIN_VOLUME <= self._volume <= self.MAX_VOLUME:
            raise ValueError(
                f"Volume must be between {self.MIN_VOLUME} and {self.MAX_VOLUME}"
            )

        return await client.request(
            device_info,
            apn=self.APN,
            body_data={"volume": self._volume},
        )

    def _handle_response(
        self,
        event_bus: EventBus,
        response: dict[str, Any],
    ) -> HandlingResult:
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            event_bus.notify(
                VolumeEvent(volume=self._volume, maximum=self.MAX_VOLUME)
            )
        return result