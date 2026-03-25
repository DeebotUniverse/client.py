"""NGIOT locate-device command."""

from __future__ import annotations

from deebot_client.ngiot_client import APN_DEVICE_LOCATE

from .common import NgiotExecuteCommand


class LocateDevice(NgiotExecuteCommand):
    """Trigger the robot locator beep on NGIOT devices."""

    NAME = "seek"

    def __init__(self) -> None:
        super().__init__({})

    async def _request_ngiot(self, client, device_info):
        return await client.request(
            device_info,
            apn=APN_DEVICE_LOCATE,
            body_data={"seek": True},
        )