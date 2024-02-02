"""Api client module."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from deebot_client.hardware.deebot import get_static_device_info

from .const import PATH_API_APPSVR_APP, PATH_API_PIM_PRODUCT_IOT_MAP
from .exceptions import ApiError
from .models import ApiDeviceInfo, DeviceInfo

if TYPE_CHECKING:
    from .authentication import Authenticator

_LOGGER = logging.getLogger(__name__)


class ApiClient:
    """Api client."""

    def __init__(self, authenticator: Authenticator) -> None:
        self._authenticator = authenticator

    async def get_devices(self) -> list[DeviceInfo | ApiDeviceInfo]:
        """Get compatible devices."""
        credentials = await self._authenticator.authenticate()
        json = {
            "userid": credentials.user_id,
            "todo": "GetGlobalDeviceList",
        }
        resp = await self._authenticator.post_authenticated(PATH_API_APPSVR_APP, json)

        if resp.get("code", None) == 0:
            devices: list[DeviceInfo | ApiDeviceInfo] = []
            device: ApiDeviceInfo
            for device in resp["devices"]:
                match device.get("company"):
                    case "eco-ng":
                        static_device_info = get_static_device_info(device["class"])
                        devices.append(DeviceInfo(device, static_device_info))
                    case "eco-legacy":
                        devices.append(device)
                    case _:
                        _LOGGER.debug(
                            "Skipping device as it is not supported: %s", device
                        )
            return devices
        _LOGGER.error("Failed to get devices: %s", resp)
        msg = f"failure {resp.get('error', '')} ({resp.get('errno', '')}) on getting devices"
        raise ApiError(msg)

    async def get_product_iot_map(self) -> dict[str, Any]:
        """Get product iot map."""
        resp = await self._authenticator.post_authenticated(
            PATH_API_PIM_PRODUCT_IOT_MAP,
            {},
        )

        if resp.get("code", None) in [0, "0000"]:
            result: dict[str, Any] = {}
            for entry in resp["data"]:
                result[entry["classid"]] = entry["product"]
            return result
        _LOGGER.error("Failed to get product iot map")
        msg = f"failure {resp['error']} ({resp['errno']}) on getting product iot map"
        raise ApiError(msg)
