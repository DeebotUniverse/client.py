"""SST authentication module for NGIOT endpoint-control devices."""

from __future__ import annotations

import asyncio
import base64
from collections.abc import Mapping
from dataclasses import dataclass
from http import HTTPStatus
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

from aiohttp import ClientResponseError, ClientSession, ClientTimeout, hdrs
import orjson

from .exceptions import ApiError, ApiTimeoutError, AuthenticationError
from .logging_filter import get_logger
from .util import cancel, create_task

if TYPE_CHECKING:
    from .authentication import Authenticator
    from .models import ApiDeviceInfo, DeviceInfo

_LOGGER = get_logger(__name__)

_TIMEOUT = ClientTimeout(60)
_SST_ISSUE_PATH = "/api/new-perm/token/sst/issue"
_SST_SERVICE = "dim"
_SST_PERMISSION = "Control"


@dataclass(frozen=True)
class SstCredentials:
    """Short-lived NGIOT SST credentials."""

    token: str
    expires_at: int
    device_key: str


@dataclass(frozen=True)
class SstDeviceIdentity:
    """Normalized device identity needed for SST minting."""

    did: str
    class_id: str
    resource: str

    @property
    def endpoint(self) -> str:
        """Return DIM ACL endpoint identifier."""
        return f"Endpoint:{self.class_id}:{self.did}"

    @property
    def key(self) -> str:
        """Return stable cache key."""
        return f"{self.class_id}:{self.did}:{self.resource}"


class SstAuthenticator:
    """Mint, cache, and refresh short-lived SST credentials per device."""

    def __init__(
        self,
        session: ClientSession,
        authenticator: Authenticator,
        *,
        base_url: str,
        requested_ttl: int = 600,
        refresh_skew: int = 60,
    ) -> None:
        self._session = session
        self._authenticator = authenticator
        self._base_url = base_url.rstrip("/")
        self._requested_ttl = requested_ttl
        self._refresh_skew = refresh_skew

        self._lock = asyncio.Lock()
        self._credentials: dict[str, SstCredentials] = {}
        self._devices: dict[str, SstDeviceIdentity] = {}
        self._refresh_handles: dict[str, asyncio.TimerHandle] = {}
        self._tasks: set[asyncio.Future[Any]] = set()

    async def get_credentials(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        *,
        force: bool = False,
    ) -> SstCredentials:
        """Return cached SST credentials for a device, refreshing if needed."""
        identity = self._normalize_device(device)

        async with self._lock:
            cached = self._credentials.get(identity.key)
            now = int(time.time())

            if (
                not force
                and cached is not None
                and cached.expires_at > now + self._refresh_skew
            ):
                return cached

            credentials = await self._issue_sst(identity)
            self._devices[identity.key] = identity
            self._credentials[identity.key] = credentials

            self._cancel_refresh_task(identity.key)
            self._create_refresh_task(identity, credentials)

            return credentials

    async def get_token(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
        *,
        force: bool = False,
    ) -> str:
        """Return SST bearer token for a device."""
        return (await self.get_credentials(device, force=force)).token

    async def invalidate(
        self,
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any] | str,
    ) -> None:
        """Invalidate cached SST for a device or cache key."""
        key = device if isinstance(device, str) else self._normalize_device(device).key

        async with self._lock:
            self._credentials.pop(key, None)
            self._devices.pop(key, None)
            self._cancel_refresh_task(key)

    async def teardown(self) -> None:
        """Teardown authenticator and cancel outstanding refresh tasks."""
        for key in list(self._refresh_handles):
            self._cancel_refresh_task(key)

        self._credentials.clear()
        self._devices.clear()
        await cancel(self._tasks)

    async def _issue_sst(self, identity: SstDeviceIdentity) -> SstCredentials:
        """Mint a fresh SST for the given device."""
        account_credentials = await self._authenticator.authenticate()

        headers = {
            hdrs.AUTHORIZATION: f"Bearer {account_credentials.token}",
            hdrs.CONTENT_TYPE: "application/json; charset=utf-8",
        }
        payload = {
            "acl": [
                {
                    "policy": [
                        {
                            "obj": [identity.endpoint],
                            "perms": [_SST_PERMISSION],
                        }
                    ],
                    "svc": _SST_SERVICE,
                }
            ],
            "exp": self._requested_ttl,
            "sub": account_credentials.user_id,
        }

        url = urljoin(self._base_url, _SST_ISSUE_PATH)
        logger_request_params = {
            "url": url,
            "device_key": identity.key,
        }

        try:
            _LOGGER.debug("Calling SST issue endpoint: %s", logger_request_params)

            async with self._session.post(
                url,
                json=payload,
                headers=headers,
                timeout=_TIMEOUT,
            ) as res:
                res.raise_for_status()
                response_data = self._parse_response_body(await res.read())

            _LOGGER.debug(
                "SST issue response for %s returned code=%s",
                identity.key,
                response_data.get("code"),
            )

            if response_data.get("code") not in (0, "0000"):
                msg = (
                    f"failure code {response_data.get('code')} "
                    f"({response_data.get('msg')}) for call {_SST_ISSUE_PATH}"
                )
                raise AuthenticationError(msg)

            token = self._extract_token(response_data)
            expires_at = self._decode_exp(token)
            if expires_at is None:
                # Fallback if the token format changes or exp is absent.
                expires_at = int(time.time()) + max(60, int(self._requested_ttl * 0.9))

            return SstCredentials(
                token=token,
                expires_at=expires_at,
                device_key=identity.key,
            )

        except TimeoutError as ex:
            raise ApiTimeoutError(path=_SST_ISSUE_PATH, timeout=_TIMEOUT) from ex
        except ClientResponseError as ex:
            if ex.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                raise AuthenticationError(
                    "SST issue request was not authorized"
                ) from ex
            raise ApiError from ex

    def _create_refresh_task(
        self,
        identity: SstDeviceIdentity,
        credentials: SstCredentials,
    ) -> None:
        """Create refresh task for a given SST credential."""

        def refresh() -> None:
            _LOGGER.debug("Refreshing SST for %s", identity.key)

            async def async_refresh() -> None:
                try:
                    await self.get_credentials(
                        identity_as_mapping(identity), force=True
                    )
                except Exception:
                    _LOGGER.exception(
                        "An exception occurred during SST refresh for %s",
                        identity.key,
                    )

            create_task(self._tasks, async_refresh())
            self._refresh_handles.pop(identity.key, None)

        seconds_until_refresh = max(
            5,
            credentials.expires_at - int(time.time()) - self._refresh_skew,
        )
        self._refresh_handles[identity.key] = asyncio.get_running_loop().call_later(
            seconds_until_refresh,
            refresh,
        )

    def _cancel_refresh_task(self, key: str) -> None:
        """Cancel refresh timer for a cache key."""
        handle = self._refresh_handles.pop(key, None)
        if handle and not handle.cancelled():
            handle.cancel()

    @staticmethod
    def _decode_exp(token: str) -> int | None:
        """Decode exp claim from SST token without signature validation."""
        try:
            parts = token.split(".")
            if len(parts) == 4 and parts[0] == "SST":
                payload_segment = parts[2]
            elif len(parts) == 3:
                payload_segment = parts[1]
            else:
                return None

            padded = payload_segment + "=" * (-len(payload_segment) % 4)
            payload = orjson.loads(base64.urlsafe_b64decode(padded))
            exp = payload.get("exp")

            return int(exp) if exp is not None else None
        except Exception:
            _LOGGER.debug("Failed to decode SST token expiry", exc_info=True)
            return None

    @staticmethod
    def _extract_token(response_data: Mapping[str, Any]) -> str:
        """Extract SST token from the issue response."""
        try:
            token = response_data["data"]["data"]["token"]
        except (KeyError, TypeError) as ex:
            msg = "SST issue response did not contain a token"
            raise AuthenticationError(msg) from ex
        return str(token)

    @staticmethod
    def _parse_response_body(body: bytes) -> dict[str, Any]:
        """Parse an SST issue response body."""
        if not body:
            msg = "SST issue response was empty"
            raise AuthenticationError(msg)
        response = orjson.loads(body)
        if not isinstance(response, dict):
            msg = "SST issue response was not a JSON object"
            raise AuthenticationError(msg)
        return response

    @staticmethod
    def _normalize_device(
        device: ApiDeviceInfo | DeviceInfo | Mapping[str, Any],
    ) -> SstDeviceIdentity:
        """Normalize a device object into the fields required for SST issuance."""
        raw_device = device.api if hasattr(device, "api") else device

        if not isinstance(raw_device, Mapping):
            msg = f"Unsupported device type for SST authentication: {type(device)!r}"
            raise TypeError(msg)

        try:
            return SstDeviceIdentity(
                did=str(raw_device["did"]),
                class_id=str(raw_device["class"]),
                resource=str(raw_device["resource"]),
            )
        except KeyError as ex:
            msg = f"Missing required SST device field: {ex.args[0]}"
            raise ApiError(msg) from ex


def identity_as_mapping(identity: SstDeviceIdentity) -> dict[str, str]:
    """Convert normalized identity back to a mapping accepted by get_credentials."""
    return {
        "did": identity.did,
        "class": identity.class_id,
        "resource": identity.resource,
    }
