"""NGIOT endpoint-control transport client."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from http import HTTPStatus
import secrets
import string
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

from aiohttp import ClientResponseError, ClientSession, ClientTimeout, hdrs
import orjson

from .exceptions import ApiError, ApiTimeoutError, AuthenticationError
from .logging_filter import get_logger

if TYPE_CHECKING:
    from .models import ApiDeviceInfo, DeviceInfo
    from .sst_authentication import SstAuthenticator

_LOGGER = get_logger(__name__)

_TIMEOUT = ClientTimeout(60)

_PATH_ENDPOINT_CONTROL = "/api/iot/endpoint/control"
_DEFAULT_FMT = "j"
_DEFAULT_CT = "q"

# Some devices transiently return "cmd busy" while state is changing.
_TRANSIENT_RESPONSE_CODES = {1}
_TRANSIENT_RESPONSE_MESSAGES = {"cmd busy"}


@dataclass(frozen=True, kw_only=True)
class NgiotClientConfiguration:
    """Transport-level defaults for NGIOT endpoint-control calls."""

    user_agent: str = "okhttp/4.9.1"
    channel: str = "Android"
    protocol_version: str = "0.0.22"
    timezone_name: str = "UTC"
    timezone_offset_minutes: int = 0
    override_control_host: str | None = None


@dataclass(frozen=True, kw_only=True)
class NgiotRequest:
    """A single NGIOT endpoint-control request."""

    apn: str | int
    body_data: Mapping[str, Any] | Sequence[Any]
    fmt: str = _DEFAULT_FMT
    ct: str = _DEFAULT_CT
    force_sst_refresh: bool = False


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
        """Return stable cache key."""
        return f"{self.class_id}:{self.did}:{self.resource}"

    @property
    def base_url(self) -> str:
        """Return normalized HTTPS base URL for NGIOT control."""
        if self.control_host.startswith(("http://", "https://")):
            return self.control_host.rstrip("/")
        return f"https://{self.control_host}".rstrip("/")


class NgiotClient:
    """Thin client for generic NGIOT endpoint-control reads and writes."""

    def __init__(
        self,
        session: ClientSession,
        sst_authenticator: SstAuthenticator,
        config: NgiotClientConfiguration | None = None,
    ) -> None:
        self._session = session
        self._sst_authenticator = sst_authenticator
        self._config = config or NgiotClientConfiguration()

    async def request(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        request: NgiotRequest,
    ) -> dict[str, Any]:
        """Execute a single NGIOT endpoint-control request."""
        identity = self._normalize_device(device)
        return await self._request_with_fallback(identity, device, request)

    async def query_fields(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        *,
        apn: str | int,
        fields: Sequence[str],
        map_id: str | int | None = None,
    ) -> Any:
        """Query a field-based NGIOT surface and return ``body.data``."""
        body_data: dict[str, Any] = {"fields": list(fields)}
        if map_id is not None:
            body_data["mapId"] = str(map_id)

        response = await self.request(
            device,
            NgiotRequest(apn=apn, body_data=body_data),
        )
        return self._extract_body_data(response)

    async def write_data(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        *,
        apn: str | int,
        data: Mapping[str, Any],
    ) -> Any:
        """Send a direct key/value NGIOT payload and return ``body.data``."""
        response = await self.request(
            device,
            NgiotRequest(apn=apn, body_data=dict(data)),
        )
        return self._extract_body_data(response)

    async def _request_with_fallback(
        self,
        identity: NgiotDeviceIdentity,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        request: NgiotRequest,
    ) -> dict[str, Any]:
        """Execute an NGIOT request and fall back to ``service.mqs`` on 404."""
        try:
            return await self._request_once(identity, device, request)
        except ClientResponseError as ex:
            if not self._should_retry_with_fallback(identity, ex):
                raise ApiError from ex

            fallback_identity = NgiotDeviceIdentity(
                did=identity.did,
                class_id=identity.class_id,
                resource=identity.resource,
                control_host=str(identity.fallback_control_host),
                fallback_control_host=None,
            )
            _LOGGER.info(
                "NGIOT endpoint-control returned 404 on %s for %s; retrying with %s",
                identity.base_url,
                identity.key,
                fallback_identity.base_url,
            )
            try:
                return await self._request_once(fallback_identity, device, request)
            except ClientResponseError as fallback_ex:
                raise ApiError from fallback_ex

    async def _request_once(
        self,
        identity: NgiotDeviceIdentity,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        request: NgiotRequest,
    ) -> dict[str, Any]:
        """Execute one endpoint-control request against one control host."""
        url = urljoin(identity.base_url + "/", _PATH_ENDPOINT_CONTROL.lstrip("/"))
        request_id = self._new_request_id()
        payload = {
            "body": {"data": self._build_payload(request.body_data)},
            "header": self._create_body_header(self._new_body_reqid()),
        }
        query_params = self._query_params(identity, request, request_id)
        headers = await self._headers(identity, request, request_id)
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
                data=orjson.dumps(payload),
                headers=headers,
                timeout=_TIMEOUT,
            ) as res:
                res.raise_for_status()
                response_data = self._parse_response_body(await res.read())

            _LOGGER.debug(
                "Success calling NGIOT api %s, response=%s",
                logger_request_params,
                response_data,
            )

            validation = self._classify_response(response_data)
            if validation == "retry_busy":
                _LOGGER.debug(
                    "NGIOT request returned transient busy for %s apn=%s; retrying once",
                    identity.key,
                    request.apn,
                )
                await asyncio.sleep(1)
                return await self._request_retry_after_busy(identity, device, request)

            return response_data

        except TimeoutError as ex:
            raise ApiTimeoutError(path=_PATH_ENDPOINT_CONTROL, timeout=_TIMEOUT) from ex
        except ClientResponseError as ex:
            if self._should_retry_with_fresh_sst(request, ex):
                _LOGGER.info(
                    "NGIOT request unauthorized for %s. Invalidating SST and retrying once.",
                    identity.key,
                )
                await self._sst_authenticator.invalidate(self._device_mapping(identity))
                refreshed_request = NgiotRequest(
                    apn=request.apn,
                    body_data=request.body_data,
                    fmt=request.fmt,
                    ct=request.ct,
                    force_sst_refresh=True,
                )
                return await self._request_with_fallback(
                    identity,
                    device,
                    refreshed_request,
                )

            if ex.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                raise AuthenticationError(
                    "NGIOT endpoint-control request was not authorized"
                ) from ex

            if ex.status == HTTPStatus.NOT_FOUND:
                raise

            _LOGGER.debug(
                "NGIOT request failed: %s", logger_request_params, exc_info=True
            )
            raise ApiError from ex

    async def _request_retry_after_busy(
        self,
        identity: NgiotDeviceIdentity,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        request: NgiotRequest,
    ) -> dict[str, Any]:
        """Retry once after a transient busy response."""
        retry_response = await self._request_with_fallback(identity, device, request)
        self._validate_response(retry_response)
        return retry_response

    def _normalize_device(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
    ) -> NgiotDeviceIdentity:
        """Normalize raw API device payload into NGIOT routing fields."""
        raw_device = device.api if hasattr(device, "api") else device

        if not isinstance(raw_device, Mapping):
            msg = f"Unsupported device type for NGIOT client: {type(device)!r}"
            raise TypeError(msg)

        service_mqs_host = self._service_mqs_host(raw_device)
        control_host = self._config.override_control_host or service_mqs_host

        if not control_host:
            msg = "Missing NGIOT control host in device service binding"
            raise ApiError(msg)

        try:
            return NgiotDeviceIdentity(
                did=str(raw_device["did"]),
                class_id=str(raw_device["class"]),
                resource=str(raw_device["resource"]),
                control_host=str(control_host),
                fallback_control_host=(
                    service_mqs_host
                    if service_mqs_host and service_mqs_host != str(control_host)
                    else None
                ),
            )
        except KeyError as ex:
            msg = f"Missing required NGIOT device field: {ex.args[0]}"
            raise ApiError(msg) from ex

    def _query_params(
        self,
        identity: NgiotDeviceIdentity,
        request: NgiotRequest,
        request_id: str,
    ) -> dict[str, str]:
        return {
            "si": request_id,
            "ct": request.ct,
            "eid": identity.did,
            "et": identity.class_id,
            "er": identity.resource,
            "apn": str(request.apn),
            "fmt": request.fmt,
        }

    async def _headers(
        self,
        identity: NgiotDeviceIdentity,
        request: NgiotRequest,
        request_id: str,
    ) -> dict[str, str]:
        token = await self._sst_authenticator.get_token(
            self._device_mapping(identity),
            force=request.force_sst_refresh,
        )
        return {
            hdrs.AUTHORIZATION: f"Bearer {token}",
            "x-eco-request-id": request_id,
            hdrs.CONTENT_TYPE: "application/octet-stream",
            hdrs.USER_AGENT: self._config.user_agent,
        }

    def _create_body_header(self, reqid: str) -> dict[str, Any]:
        """Create request body header matching the observed mobile shape."""
        return {
            "channel": self._config.channel,
            "m": "request",
            "pri": 2,
            "reqid": reqid,
            "ts": str(int(time.time() * 1000)),
            "tzc": self._config.timezone_name,
            "tzm": self._config.timezone_offset_minutes,
            "ver": self._config.protocol_version,
        }

    @staticmethod
    def _build_payload(
        body_data: Mapping[str, Any] | Sequence[Any],
    ) -> Mapping[str, Any] | Sequence[Any]:
        """Return a copy of mapping payloads without command-specific mutation."""
        if isinstance(body_data, Mapping):
            return dict(body_data)
        return body_data

    @staticmethod
    def _extract_body_data(response: Mapping[str, Any]) -> Any:
        """Return body.data, defaulting ACK-only responses to an empty dict."""
        body = response.get("body")
        if not isinstance(body, Mapping):
            return {}
        return body.get("data", {})

    @classmethod
    def _classify_response(cls, response: Mapping[str, Any] | None) -> str:
        """Classify NGIOT envelope and support ACK-only or transient-busy replies."""
        if response is None:
            _LOGGER.debug("Empty NGIOT response body returned by server")
            return "ok"

        body = response.get("body")
        if not isinstance(body, Mapping):
            _LOGGER.debug("NGIOT response omitted body; treating as ACK-only success")
            return "ok"

        code = body.get("code", 0)
        msg = str(body.get("msg", "")).strip().lower()

        if code in (0, "0000", None):
            return "ok"

        if code in _TRANSIENT_RESPONSE_CODES and msg in _TRANSIENT_RESPONSE_MESSAGES:
            return "retry_busy"

        msg_0 = (
            f"NGIOT request failed with code {code} ({body.get('msg', 'unknown error')}) "
            f"for {_PATH_ENDPOINT_CONTROL}"
        )
        raise ApiError(msg_0)

    @staticmethod
    def _validate_response(response: Mapping[str, Any] | None) -> None:
        """Validate NGIOT envelope and raise ApiError on device-side failures."""
        if response is None:
            _LOGGER.debug("Empty NGIOT response body returned by server")
            return

        if not isinstance(response, Mapping):
            raise ApiError("Invalid NGIOT response: missing body")

        body = response.get("body")
        if body is None:
            if isinstance(response.get("header"), Mapping):
                _LOGGER.debug("NGIOT ACK-only response without body: %s", response)
                return
            raise ApiError("Invalid NGIOT response: missing body")

        if not isinstance(body, Mapping):
            raise ApiError("Invalid NGIOT response: missing body")

        code = body.get("code", 0)
        if code not in (0, "0000", None):
            msg = body.get("msg", "unknown error")
            msg_0 = f"NGIOT request failed with code {code} ({msg}) for {_PATH_ENDPOINT_CONTROL}"
            raise ApiError(msg_0)

    @staticmethod
    def _parse_response_body(body: bytes) -> dict[str, Any]:
        """Parse an endpoint-control JSON response body."""
        if not body:
            return {}
        response = orjson.loads(body)
        if not isinstance(response, dict):
            raise ApiError("Invalid NGIOT response: expected JSON object")
        return response

    @staticmethod
    def _should_retry_with_fallback(
        identity: NgiotDeviceIdentity,
        ex: ClientResponseError,
    ) -> bool:
        return (
            ex.status == HTTPStatus.NOT_FOUND
            and identity.fallback_control_host is not None
            and identity.fallback_control_host != identity.control_host
        )

    @staticmethod
    def _should_retry_with_fresh_sst(
        request: NgiotRequest,
        ex: ClientResponseError,
    ) -> bool:
        return (
            ex.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN)
            and not request.force_sst_refresh
        )

    @staticmethod
    def _service_mqs_host(raw_device: Mapping[str, Any]) -> str | None:
        service = raw_device.get("service", {})
        if isinstance(service, Mapping):
            candidate = service.get("mqs")
            if isinstance(candidate, str) and candidate:
                return candidate
        return None

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
    def _device_mapping(identity: NgiotDeviceIdentity) -> dict[str, Any]:
        """Convert identity into a mapping accepted by SstAuthenticator."""
        return {
            "did": identity.did,
            "class": identity.class_id,
            "resource": identity.resource,
            "service": {"mqs": identity.control_host},
        }
