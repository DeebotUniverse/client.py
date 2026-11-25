"""SST authentication for NGIOT devices."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
from http import HTTPStatus
import time
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from aiohttp import ClientError, ClientResponseError, ClientTimeout, hdrs
import orjson

from .exceptions import ApiError, ApiTimeoutError, AuthenticationError

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from .authentication import Authenticator
    from .models import ApiDeviceInfo

_TIMEOUT = ClientTimeout(60)
_SST_ISSUE_PATH = "/api/new-perm/token/sst/issue"
_REQUESTED_TTL = 600
_REFRESH_SKEW = 60


@dataclass(frozen=True, kw_only=True)
class _SstCredentials:
    """Device-scoped SST credentials."""

    token: str = field(repr=False)
    expires_at: int


class SstAuthenticator:
    """Obtain and cache short-lived SST tokens for NGIOT devices."""

    def __init__(
        self, session: ClientSession, authenticator: Authenticator, *, base_url: str
    ) -> None:
        self._session = session
        self._authenticator = authenticator
        self._url = urljoin(base_url, _SST_ISSUE_PATH)
        self._lock = asyncio.Lock()
        self._credentials: dict[tuple[str, str, str], _SstCredentials] = {}

    async def get_token(self, device: ApiDeviceInfo, *, force: bool = False) -> str:
        """Return a device token, renewing it on demand before expiry."""
        key = (device["class"], device["did"], device["resource"])
        async with self._lock:
            credentials = self._credentials.get(key)
            if (
                force
                or credentials is None
                or credentials.expires_at <= time.time() + _REFRESH_SKEW
            ):
                credentials = await self._issue_sst(device)
                self._credentials[key] = credentials
            return credentials.token

    async def invalidate(self, device: ApiDeviceInfo) -> None:
        """Discard a device token so the next request obtains a new one."""
        key = (device["class"], device["did"], device["resource"])
        async with self._lock:
            self._credentials.pop(key, None)

    async def _issue_sst(self, device: ApiDeviceInfo) -> _SstCredentials:
        credentials = await self._authenticator.authenticate()
        payload = {
            "acl": [
                {
                    "policy": [
                        {
                            "obj": [f"Endpoint:{device['class']}:{device['did']}"],
                            "perms": ["Control"],
                        }
                    ],
                    "svc": "dim",
                }
            ],
            "exp": _REQUESTED_TTL,
            "sub": credentials.user_id,
        }
        headers = {
            hdrs.AUTHORIZATION: f"Bearer {credentials.token}",
            hdrs.CONTENT_TYPE: "application/json; charset=utf-8",
        }
        requested_at = int(time.time())
        try:
            async with self._session.post(
                self._url,
                data=orjson.dumps(payload),
                headers=headers,
                timeout=_TIMEOUT,
            ) as response:
                response.raise_for_status()
                # The API may return JSON with a non-JSON content type.
                response_data = await response.json(
                    content_type=None, loads=orjson.loads
                )
        except TimeoutError as ex:
            raise ApiTimeoutError(path=_SST_ISSUE_PATH, timeout=_TIMEOUT) from ex
        except ClientResponseError as ex:
            if ex.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                raise AuthenticationError(
                    "SST issue request was not authorized"
                ) from ex
            raise ApiError("SST issue request failed") from ex
        except ClientError as ex:
            raise ApiError("SST issue request failed") from ex
        except orjson.JSONDecodeError as ex:
            raise AuthenticationError("Invalid SST issue response") from ex

        if not isinstance(response_data, dict) or response_data.get("code") not in (
            0,
            "0000",
        ):
            raise AuthenticationError("SST issue request was rejected")
        try:
            token = response_data["data"]["data"]["token"]
        except (KeyError, TypeError) as ex:
            raise AuthenticationError("Invalid SST issue response") from ex
        if not isinstance(token, str) or not token:
            raise AuthenticationError("Invalid SST token")

        expires_at = _decode_expiry(token)
        if expires_at is None:
            # Preserve the reference implementation's conservative TTL fallback.
            expires_at = requested_at + int(_REQUESTED_TTL * 0.9)
        if expires_at <= time.time():
            raise AuthenticationError("SST token has expired")
        return _SstCredentials(token=token, expires_at=expires_at)


def _decode_expiry(token: str) -> int | None:
    """Read the expiry claim for cache scheduling, not token verification."""
    parts = token.split(".")
    if len(parts) == 4 and parts[0] == "SST":
        segment = parts[2]
    elif len(parts) == 3:
        segment = parts[1]
    else:
        return None

    try:
        payload = orjson.loads(
            base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
        )
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    expiry = payload.get("exp")
    if isinstance(expiry, int) and not isinstance(expiry, bool):
        return expiry
    return None
