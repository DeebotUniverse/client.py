"""Api client module."""
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from ._api_client import _InternalApiClient
from .authentication import Authenticator
from .command import Command
from .commands import GetCleanLogs
from .commands.custom import CustomCommand
from .const import (
    PATH_API_APPSVR_APP,
    PATH_API_IOT_DEVMANAGER,
    PATH_API_LG_LOG,
    PATH_API_PIM_PRODUCT_IOT_MAP,
)
from .exceptions import ApiError
from .logging_filter import get_logger
from .models import Configuration, DeviceInfo

_LOGGER = get_logger(__name__)
_REQUEST_HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 5.1.1; A5010 Build/LMY48Z)",
}


def _get_portal_url(config: Configuration, path: str) -> str:
    subdomain = f"portal-{config.continent}" if config.country != "cn" else "portal"
    return urljoin(f"https://{subdomain}.ecouser.net/api/", path)


class ApiClient:
    """Api client."""

    def __init__(
        self, internal_api_client: _InternalApiClient, authenticator: Authenticator
    ):
        self._api_client = internal_api_client
        self._authenticator = authenticator

    async def get_devices(self) -> list[DeviceInfo]:
        """Get compatible devices."""
        credentials = await self._authenticator.authenticate()
        json = {
            "userid": credentials.user_id,
            "todo": "GetGlobalDeviceList",
        }
        resp = await self._api_client.post(
            PATH_API_APPSVR_APP, json, credentials=credentials
        )

        if resp.get("code", None) == 0:
            devices: list[DeviceInfo] = []
            for device in resp["devices"]:
                if device.get("company") == "eco-ng":
                    devices.append(DeviceInfo(device))
                else:
                    _LOGGER.debug("Skipping device as it is not supported: %s", device)
            return devices
        _LOGGER.error("Failed to get devices")
        raise ApiError(f"failure {resp['error']} ({resp['errno']}) on getting devices")

    async def get_product_iot_map(self) -> dict[str, Any]:
        """Get product iot map."""
        resp = await self._api_client.post(
            PATH_API_PIM_PRODUCT_IOT_MAP,
            {},
            credentials=await self._authenticator.authenticate(),
        )

        if resp.get("code", None) in [0, "0000"]:
            result: dict[str, Any] = {}
            for entry in resp["data"]:
                result[entry["classid"]] = entry["product"]
            return result
        _LOGGER.error("Failed to get product iot map")
        raise ApiError(
            f"failure {resp['error']} ({resp['errno']}) on getting product iot map"
        )

    async def send_command(
        self,
        command: Command | CustomCommand,
        device_info: DeviceInfo,
    ) -> dict[str, Any]:
        """Send json command for given vacuum to the api."""
        query_params = {}
        json: dict[str, Any]

        if command.name == GetCleanLogs.name:
            json = {
                "td": command.name,
                "did": device_info.did,
                "resource": device_info.resource,
            }

            path = PATH_API_LG_LOG
        else:
            payload = {
                "header": {
                    "pri": "1",
                    "ts": datetime.now().timestamp(),
                    "tzm": 480,
                    "ver": "0.0.50",
                }
            }

            if len(command.args) > 0:
                payload["body"] = {"data": command.args}

            json = {
                "cmdName": command.name,
                "payload": payload,
                "payloadType": "j",
                "td": "q",
                "toId": device_info.did,
                "toRes": device_info.resource,
                "toType": device_info.get_class,
            }

            path = PATH_API_IOT_DEVMANAGER
            query_params.update({"mid": json["toType"], "did": json["toId"]})

        credentials = await self._authenticator.authenticate()
        query_params.update(
            {
                "td": json["td"],
                "u": credentials.user_id,
                "cv": "1.67.3",
                "t": "a",
                "av": "1.3.1",
            }
        )

        return await self._api_client.post(
            path,
            json,
            query_params=query_params,
            headers=_REQUEST_HEADERS,
            credentials=credentials,
        )
