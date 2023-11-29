"""Api client module."""
from typing import Any

from deebot_client.hardware.deebot import get_static_device_info

from .authentication import Authenticator
from .const import PATH_API_APPSVR_APP, PATH_API_PIM_PRODUCT_IOT_MAP
from .exceptions import ApiError
from .logging_filter import get_logger
from .models import ApiDeviceInfo, DeviceInfo

_LOGGER = get_logger(__name__)


class ApiClient:
    """Api client."""

    def __init__(self, authenticator: Authenticator) -> None:
        self._authenticator = authenticator

    async def get_devices(self) -> list[DeviceInfo]:
        """Get compatible devices."""
        credentials = await self._authenticator.authenticate()
        json = {
            "userid": credentials.user_id,
            "todo": "GetGlobalDeviceList",
        }
        resp = await self._authenticator.post_authenticated(PATH_API_APPSVR_APP, json)

        if resp.get("code", None) == 0:
            devices: list[DeviceInfo] = []
            device: ApiDeviceInfo
            for device in resp["devices"]:
                if device.get("company") == "eco-ng":
                    static_device_info = get_static_device_info(device["class"])
                    devices.append(DeviceInfo(device, static_device_info))
                else:
                    _LOGGER.debug("Skipping device as it is not supported: %s", device)
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
