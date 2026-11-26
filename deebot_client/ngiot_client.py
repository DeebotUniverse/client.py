"""HTTP transport for NGIOT endpoint control."""

from __future__ import annotations

from http import HTTPStatus
import re
import secrets
import string
import time
from typing import TYPE_CHECKING, Any

from aiohttp import ClientError, ClientResponseError, ClientTimeout, hdrs
import orjson

from .exceptions import ApiError, ApiTimeoutError, AuthenticationError

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from .models import ApiDeviceInfo, Credentials

_PATH = "/api/iot/endpoint/control"
_TIMEOUT = ClientTimeout(60)
_HOST_PATTERN = re.compile(r"api-ngiot(?:\.[a-z0-9-]+)+\.ecouser\.net")


def _control_url(device: ApiDeviceInfo) -> str:
    """Use the device's NGIOT service binding, not the account region."""
    service = device.get("service")
    host = service.get("mqs") if isinstance(service, dict) else None
    if not isinstance(host, str) or not _HOST_PATTERN.fullmatch(host):
        raise ApiError("Missing or invalid NGIOT control host")
    return f"https://{host}{_PATH}"


def _request_id(length: int) -> str:
    return "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(length)
    )


class NgiotClient:
    """Send NGIOT JSON requests using existing account credentials."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def request(
        self,
        credentials: Credentials,
        device: ApiDeviceInfo,
        apn: str,
        data: dict[str, Any] | list[Any],
    ) -> dict[str, Any]:
        """Return the endpoint response without interpreting command results."""
        url = _control_url(device)
        request_id = _request_id(16)
        params = {
            "si": request_id,
            "ct": "q",
            "eid": device["did"],
            "et": device["class"],
            "er": device["resource"],
            "apn": apn,
            "fmt": "j",
        }
        payload = {
            "header": {
                "channel": "iOS",
                "m": "request",
                "pri": 1,
                "reqid": _request_id(6),
                "ts": str(int(time.time() * 1000)),
                "tzc": "UTC",
                "tzm": 0,
                "ver": "0.0.50",
            },
            "body": {"data": data},
        }
        headers = {
            hdrs.ACCEPT: "*/*",
            hdrs.AUTHORIZATION: f"Bearer {credentials.token}",
            hdrs.CONTENT_TYPE: "application/octet-stream",
            hdrs.USER_AGENT: "EcovacsHome/287541 CFNetwork Darwin",
            "x-eco-request-id": request_id,
        }

        try:
            async with self._session.post(
                url,
                params=params,
                data=orjson.dumps(payload),
                headers=headers,
                timeout=_TIMEOUT,
                allow_redirects=False,
            ) as response:
                response.raise_for_status()
                status = response.status
                result = (
                    await response.json(content_type=None, loads=orjson.loads)
                    if status == HTTPStatus.OK
                    else None
                )
        except TimeoutError as ex:
            raise ApiTimeoutError(path=_PATH, timeout=_TIMEOUT) from ex
        except ClientResponseError as ex:
            if ex.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                raise AuthenticationError("NGIOT request was not authorized") from ex
            raise ApiError("NGIOT HTTP request failed") from ex
        except (ClientError, ValueError) as ex:
            raise ApiError("NGIOT request or response failed") from ex

        if status != HTTPStatus.OK:
            raise ApiError("Unexpected NGIOT HTTP status")
        if not isinstance(result, dict) or not isinstance(result.get("body"), dict):
            raise ApiError("Invalid NGIOT response envelope")
        code = result["body"].get("code")
        if isinstance(code, bool) or not isinstance(code, (int, str)):
            raise ApiError("Missing or invalid NGIOT response code")
        return result
