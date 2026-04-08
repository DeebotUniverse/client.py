"""NGIOT play-sound commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.ngiot_client import APN_DEVICE_LOCATE

from .common import NgiotExecuteCommand

if TYPE_CHECKING:
    from deebot_client.models import ApiDeviceInfo
    from deebot_client.ngiot_client import NgiotClient


class PlaySound(NgiotExecuteCommand):
    """Trigger device locate sound."""

    NAME = "seek"

    def __init__(self) -> None:
        super().__init__({})

    async def _request_ngiot(
        self,
        client: NgiotClient,
        device_info: ApiDeviceInfo,
    ) -> dict[str, object]:
        return await client.request(
            device_info,
            apn=APN_DEVICE_LOCATE,
            body_data={"seek": True},
        )