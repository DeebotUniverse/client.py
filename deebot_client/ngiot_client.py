"""NGIOT endpoint-control client for eco-ng devices such as eyfj07."""

from __future__ import annotations

import json
import secrets
import string
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

from aiohttp import ClientResponseError, ClientSession, ClientTimeout, hdrs

from .exceptions import ApiError, ApiTimeoutError, AuthenticationError
from .logging_filter import get_logger
from .sst_authentication import SstAuthenticator

if TYPE_CHECKING:
    from .models import ApiDeviceInfo, DeviceInfo

_LOGGER = get_logger(__name__)

_TIMEOUT = ClientTimeout(60)

_PATH_ENDPOINT_CONTROL = "/api/iot/endpoint/control"
_DEFAULT_FMT = "j"
_DEFAULT_CT = "q"

APN_ROBOT_DETAIL = "10001"
APN_MAP_DETAILS = "30001"
APN_CLEAN_START = "40001"
APN_AREA_CLEAN = "40007"
APN_PAUSE = "40009"
APN_RESUME = "40011"
APN_RETURN_TO_DOCK = "40013"
APN_CANCEL_RETURN = "40015"
APN_DEVICE_LOCATE = "40019"


@dataclass(frozen=True)
class NgiotDeviceIdentity:
    """Normalized NGIOT device identity."""

    did: str
    class_id: str
    resource: str
    control_host: str
    fallback_control_host: str | None = None

    @property
    def key(self) -> str:
        """Stable cache/logging key."""
        return f"{self.class_id}:{self.did}:{self.resource}"

    @property
    def base_url(self) -> str:
        """Normalized HTTPS base URL for NGIOT control."""
        if self.control_host.startswith(("http://", "https://")):
            return self.control_host.rstrip("/")
        return f"https://{self.control_host}".rstrip("/")


class NgiotClient:
    """Thin client for NGIOT endpoint-control reads and writes."""

    def __init__(
        self,
        session: ClientSession,
        sst_authenticator: SstAuthenticator,
        *,
        user_agent: str = "okhttp/4.9.1",
        channel: str = "Android",
        protocol_version: str = "0.0.22",
        timezone_name: str = "UTC",
        timezone_offset_minutes: int = 0,
        override_control_host: str | None = None,
    ) -> None:
        self._session = session
        self._sst_authenticator = sst_authenticator
        self._user_agent = user_agent
        self._channel = channel
        self._protocol_version = protocol_version
        self._timezone_name = timezone_name
        self._timezone_offset_minutes = timezone_offset_minutes
        self._override_control_host = override_control_host

    async def request(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        *,
        apn: str | int,
        body_data: Mapping[str, Any] | Sequence[Any],
        fmt: str = _DEFAULT_FMT,
        ct: str = _DEFAULT_CT,
        force_sst_refresh: bool = False,
    ) -> dict[str, Any]:
        """Execute a single NGIOT endpoint-control request.

        Returns the full decoded NGIOT JSON envelope:
        {
            "body": {...},
            "header": {...}
        }
        """
        identity = self._normalize_device(device)
        return await self._request_with_fallback(
            identity,
            device,
            apn=apn,
            body_data=body_data,
            fmt=fmt,
            ct=ct,
            force_sst_refresh=force_sst_refresh,
        )

    async def _request_with_fallback(
        self,
        identity: NgiotDeviceIdentity,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        *,
        apn: str | int,
        body_data: Mapping[str, Any] | Sequence[Any],
        fmt: str,
        ct: str,
        force_sst_refresh: bool,
    ) -> dict[str, Any]:
        """Execute an NGIOT request and fall back to service.mqs on 404."""
        try:
            return await self._request_once(
                identity,
                device,
                apn=apn,
                body_data=body_data,
                fmt=fmt,
                ct=ct,
                force_sst_refresh=force_sst_refresh,
            )
        except ClientResponseError as ex:
            if (
                ex.status == HTTPStatus.NOT_FOUND
                and identity.fallback_control_host
                and identity.fallback_control_host != identity.control_host
            ):
                fallback_identity = NgiotDeviceIdentity(
                    did=identity.did,
                    class_id=identity.class_id,
                    resource=identity.resource,
                    control_host=identity.fallback_control_host,
                    fallback_control_host=None,
                )
                _LOGGER.info(
                    "NGIOT endpoint-control returned 404 on %s for %s; retrying with device mqs host %s",
                    identity.base_url,
                    identity.key,
                    fallback_identity.base_url,
                )
                return await self._request_once(
                    fallback_identity,
                    device,
                    apn=apn,
                    body_data=body_data,
                    fmt=fmt,
                    ct=ct,
                    force_sst_refresh=force_sst_refresh,
                )
            raise

    async def _request_once(
        self,
        identity: NgiotDeviceIdentity,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        *,
        apn: str | int,
        body_data: Mapping[str, Any] | Sequence[Any],
        fmt: str,
        ct: str,
        force_sst_refresh: bool,
    ) -> dict[str, Any]:
        """Execute a single NGIOT endpoint-control request against one control host."""
        url = urljoin(identity.base_url + "/", _PATH_ENDPOINT_CONTROL.lstrip("/"))

        request_id = self._new_request_id()
        body_reqid = self._new_body_reqid()

        query_params = {
            "si": request_id,
            "ct": ct,
            "eid": identity.did,
            "et": identity.class_id,
            "er": identity.resource,
            "apn": str(apn),
            "fmt": fmt,
        }

        payload = {
            "body": {"data": self._build_payload(apn, body_data)},
            "header": self._create_body_header(body_reqid),
        }

        token = await self._sst_authenticator.get_token(
            self._device_mapping(identity),
            force=force_sst_refresh,
        )

        headers = {
            hdrs.AUTHORIZATION: f"Bearer {token}",
            "x-eco-request-id": request_id,
            hdrs.CONTENT_TYPE: "application/octet-stream",
            hdrs.USER_AGENT: self._user_agent,
        }

        logger_request_params = {
            "url": url,
            "query_params": query_params,
            "payload": payload,
            "device_key": identity.key,
        }

        try:
            _LOGGER.debug("Calling NGIOT api: %s", logger_request_params)

            async with self._session.post(
                url,
                params=query_params,
                data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                headers=headers,
                timeout=_TIMEOUT,
            ) as res:
                res.raise_for_status()
                content_type = res.headers.get(hdrs.CONTENT_TYPE, "").lower()
                response_data: dict[str, Any] = await res.json(
                    content_type=content_type or None
                )

            _LOGGER.debug(
                "Success calling NGIOT api %s, response=%s",
                logger_request_params,
                response_data,
            )
            _LOGGER.debug(
                "NGIOT protocol trace -> apn=%s payload=%s response=%s",
                apn,
                payload["body"]["data"],
                response_data,
            )

            self._validate_response(response_data)
            return response_data

        except TimeoutError as ex:
            raise ApiTimeoutError(path=_PATH_ENDPOINT_CONTROL, timeout=_TIMEOUT) from ex
        except ClientResponseError as ex:
            if (
                ex.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN)
                and not force_sst_refresh
            ):
                _LOGGER.info(
                    "NGIOT request unauthorized for %s. Invalidating SST and retrying once.",
                    identity.key,
                )
                await self._sst_authenticator.invalidate(self._device_mapping(identity))
                return await self._request_with_fallback(
                    identity,
                    device,
                    apn=apn,
                    body_data=body_data,
                    fmt=fmt,
                    ct=ct,
                    force_sst_refresh=True,
                )

            if ex.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                raise AuthenticationError(
                    "NGIOT endpoint-control request was not authorized"
                ) from ex

            _LOGGER.debug("NGIOT request failed: %s", logger_request_params, exc_info=True)
            raise

    async def query_fields(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        *,
        apn: str | int,
        fields: Sequence[str],
        map_id: str | int | None = None,
    ) -> Any:
        """Query a field-based NGIOT surface and return body.data."""
        body_data: dict[str, Any] = {"fields": list(fields)}
        if map_id is not None:
            body_data["mapId"] = str(map_id)

        response = await self.request(device, apn=apn, body_data=body_data)
        return self._extract_body_data(response)

    async def write_data(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        *,
        apn: str | int,
        data: Mapping[str, Any],
    ) -> Any:
        """Send a direct key/value NGIOT control payload and return body.data."""
        response = await self.request(device, apn=apn, body_data=dict(data))
        return self._extract_body_data(response)

    async def get_robot_detail(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        fields: Sequence[str],
    ) -> Any:
        """Read robot detail fields from the status surface."""
        return await self.query_fields(
            device,
            apn=APN_ROBOT_DETAIL,
            fields=fields,
        )

    async def get_map_details(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        fields: Sequence[str],
        *,
        map_id: str | int | None = None,
    ) -> Any:
        """Read map detail fields from the map surface."""
        return await self.query_fields(
            device,
            apn=APN_MAP_DETAILS,
            fields=fields,
            map_id=map_id,
        )

    async def set_pause(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        *,
        pause: bool,
    ) -> Any:
        """Pause or resume the current cleaning job."""
        return await self.write_data(
            device,
            apn=APN_PAUSE if pause else APN_RESUME,
            data={"pauseSwitch": pause},
        )

    async def set_charge(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        *,
        enabled: bool,
    ) -> Any:
        """Start or cancel dock/charge behavior."""
        return await self.write_data(
            device,
            apn=APN_RETURN_TO_DOCK if enabled else APN_CANCEL_RETURN,
            data={"chargeSwitch": enabled},
        )

    async def start_smart_clean(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
    ) -> Any:
        """Start default smart cleaning."""
        return await self.write_data(
            device,
            apn=APN_CLEAN_START,
            data={"cleanSwitch": True, "cleanMode": "smart"},
        )

    async def start_area_clean(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        room_ids: Sequence[int],
    ) -> Any:
        """Start area cleaning for one or more room IDs."""
        return await self.write_data(
            device,
            apn=APN_AREA_CLEAN,
            data={
                "cleanSwitch": True,
                "cleanMode": "area",
                "cleanValues": list(room_ids),
            },
        )

    def _normalize_device(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
    ) -> NgiotDeviceIdentity:
        """Normalize raw API device payload into NGIOT routing fields."""
        raw_device = device.api if hasattr(device, "api") else device

        if not isinstance(raw_device, Mapping):
            msg = f"Unsupported device type for NGIOT client: {type(device)!r}"
            raise TypeError(msg)

        service = raw_device.get("service", {})
        service_mqs_host = None
        if isinstance(service, Mapping):
            candidate = service.get("mqs")
            if isinstance(candidate, str) and candidate:
                service_mqs_host = candidate

        host = self._override_control_host or service_mqs_host

        if not host:
            msg = f"Missing NGIOT control host in device service binding: {raw_device}"
            raise ApiError(msg)

        try:
            return NgiotDeviceIdentity(
                did=str(raw_device["did"]),
                class_id=str(raw_device["class"]),
                resource=str(raw_device["resource"]),
                control_host=str(host),
                fallback_control_host=(
                    str(service_mqs_host)
                    if service_mqs_host and str(service_mqs_host) != str(host)
                    else None
                ),
            )
        except KeyError as ex:
            msg = f"Missing required NGIOT device field: {ex.args[0]}"
            raise ApiError(msg) from ex


    def _build_payload(
        self,
        apn: str | int,
        body_data: Mapping[str, Any] | Sequence[Any],
    ) -> Mapping[str, Any] | Sequence[Any]:
        """Build a device-tolerant NGIOT payload.

        eyfj07 rejects some empty legacy payloads with a null body.
        This helper preserves caller-provided payloads while adding a
        minimal request envelope for reads that otherwise send `{}`.
        """
        if not isinstance(body_data, Mapping):
            return body_data

        payload: dict[str, Any] = dict(body_data)
        now_ms = int(time.time() * 1000)
        now_s = int(time.time())

        payload.setdefault("reqId", str(now_ms))
        payload.setdefault("timestamp", now_s)

        apn_str = str(apn)
        if apn_str == APN_ROBOT_DETAIL:
            payload.setdefault("type", "get")
        elif apn_str == APN_MAP_DETAILS:
            payload.setdefault("mapId", str(payload.get("mapId", "0")))

        return payload

    def _create_body_header(self, reqid: str) -> dict[str, Any]:
        """Create request body header matching the observed mobile shape."""
        return {
            "channel": self._channel,
            "m": "request",
            "pri": 2,
            "reqid": reqid,
            "ts": str(int(time.time() * 1000)),
            "tzc": self._timezone_name,
            "tzm": self._timezone_offset_minutes,
            "ver": self._protocol_version,
        }

    @staticmethod
    def _extract_body_data(response: Mapping[str, Any]) -> Any:
        """Return body.data, defaulting ACK-only responses to an empty dict."""
        body = response.get("body")
        if not isinstance(body, Mapping):
            return {}
        return body.get("data", {})

    @staticmethod
    def _validate_response(response: Mapping[str, Any] | None) -> None:
        """Validate NGIOT envelope and raise ApiError on device-side failures."""
        if response is None:
            _LOGGER.debug("Empty NGIOT response body returned by server")
            return

        body = response.get("body")
        if not isinstance(body, Mapping):
            raise ApiError("Invalid NGIOT response: missing body")

        code = body.get("code", 0)
        if code not in (0, "0000", None):
            msg = body.get("msg", "unknown error")
            raise ApiError(
                f"NGIOT request failed with code {code} ({msg}) for {_PATH_ENDPOINT_CONTROL}"
            )

    @staticmethod
    def _new_request_id() -> str:
        """Generate request ID for query/header transport fields."""
        return secrets.token_hex(16)

    @staticmethod
    def _new_body_reqid(length: int = 6) -> str:
        """Generate short request ID for the NGIOT body header."""
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def _device_mapping(identity: NgiotDeviceIdentity) -> dict[str, str]:
        """Convert identity into a mapping accepted by SstAuthenticator."""
        return {
            "did": identity.did,
            "class": identity.class_id,
            "resource": identity.resource,
            "service": {"mqs": identity.control_host},
        }