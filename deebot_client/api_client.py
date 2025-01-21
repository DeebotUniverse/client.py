"""Api client module."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from deebot_client.hardware.deebot import get_static_device_info

from .const import (
    PATH_API_APPSVR_APP,
    PATH_API_PIM_PRODUCT_IOT_MAP,
    PATH_API_USERS_USER,
)
from .exceptions import ApiError
from .logging_filter import get_logger
from .models import ApiDeviceInfo, DeviceInfo

if TYPE_CHECKING:
    from .authentication import Authenticator

_LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class Devices:
    """Devices."""

    mqtt: list[DeviceInfo]
    xmpp: list[ApiDeviceInfo]
    not_supported: list[ApiDeviceInfo]


class ApiClient:
    """Api client."""

    def __init__(self, authenticator: Authenticator) -> None:
        self._authenticator = authenticator

    async def _get_devices(self, path: str, command: str) -> dict[str, ApiDeviceInfo]:
        credentials = await self._authenticator.authenticate()
        json = {
            "userid": credentials.user_id,
            "todo": command,
        }
        resp = await self._authenticator.post_authenticated(path, json)

        result = {}
        if "devices" in resp:
            device: ApiDeviceInfo
            for device in resp["devices"]:
                result[device["did"]] = device
        else:
            _LOGGER.info("Failed to get devices: %s", resp)

        return result

    async def get_devices(self) -> Devices:
        """Get compatible devices."""
        try:
            async with asyncio.TaskGroup() as tg:
                task_device_list = tg.create_task(
                    self._get_devices(PATH_API_USERS_USER, "GetDeviceList")
                )
                task_global_device_list = tg.create_task(
                    self._get_devices(PATH_API_APPSVR_APP, "GetGlobalDeviceList")
                )
        except (ExceptionGroup, BaseExceptionGroup) as ex:
            raise ApiError("Error on getting devices") from ex

        api_devices = task_device_list.result()
        api_devices.update(task_global_device_list.result())

        mqtt: list[DeviceInfo] = []
        xmpp: list[ApiDeviceInfo] = []
        not_supported: list[ApiDeviceInfo] = []
        for device in api_devices.values():
            match device.get("company"):
                case "eco-ng":
                    if static_device_info := await get_static_device_info(
                        device["class"]
                    ):
                        mqtt.append(DeviceInfo(device, static_device_info))
                    else:
                        _LOGGER.warning(
                            'Device class "%s" not recognized. Please add support for it: %s',
                            device["class"],
                            device,
                        )
                        not_supported.append(device)
                case "eco-legacy":
                    xmpp.append(device)
                case _:
                    _LOGGER.warning(
                        "Skipping device as it is not supported: %s", device
                    )
                    not_supported.append(device)

        if not mqtt and not xmpp and not not_supported:
            _LOGGER.warning("No devices returned by the api. Please check the logs.")

        return Devices(mqtt, xmpp, not_supported)

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
