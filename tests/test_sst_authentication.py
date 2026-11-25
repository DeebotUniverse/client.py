from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock, patch

from aiohttp import ClientConnectionError, ClientSession, hdrs, web
from aiohttp.test_utils import TestServer
import orjson
import pytest

from deebot_client.exceptions import ApiError, ApiTimeoutError, AuthenticationError
from deebot_client.models import Credentials
from deebot_client.sst_authentication import SstAuthenticator

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from deebot_client.models import ApiDeviceInfo

_PATH = "/api/new-perm/token/sst/issue"
_NOW = 1_800_000_000
_DEVICE: ApiDeviceInfo = {
    "class": "eyfj07",
    "did": "device-id",
    "resource": "resource-id",
    "company": "eco-ng",
    "name": "Test device",
}


def _token(expiry: int, *, sst: bool = True) -> str:
    payload = (
        base64.urlsafe_b64encode(orjson.dumps({"exp": expiry})).decode().rstrip("=")
    )
    return f"SST.header.{payload}.signature" if sst else f"header.{payload}.signature"


def _response(token: str) -> dict[str, Any]:
    return {"code": 0, "data": {"data": {"token": token}}}


@dataclass
class _SstApi:
    """Fake SST endpoint with recorded requests."""

    body: bytes = field(
        default_factory=lambda: orjson.dumps(_response(_token(_NOW + 600)))
    )
    status: int = HTTPStatus.OK
    requests: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    async def handle(self, request: web.Request) -> web.Response:
        """Return the configured response and record the request."""
        self.requests.append(
            (request.headers[hdrs.AUTHORIZATION], orjson.loads(await request.read()))
        )
        return web.Response(
            body=self.body, status=self.status, content_type="text/plain"
        )


@pytest.fixture
async def sst_api() -> AsyncGenerator[tuple[SstAuthenticator, _SstApi]]:
    api = _SstApi()
    app = web.Application()
    app.router.add_post(_PATH, api.handle)
    authenticator = Mock()
    authenticator.authenticate = AsyncMock(
        return_value=Credentials("portal-token", "user-id")
    )
    async with TestServer(app) as server, ClientSession() as session:
        with patch("deebot_client.sst_authentication.time") as clock:
            clock.time.return_value = _NOW
            yield (
                SstAuthenticator(
                    session, authenticator, base_url=str(server.make_url("/"))
                ),
                api,
            )


async def test_get_token(sst_api: tuple[SstAuthenticator, _SstApi]) -> None:
    auth, api = sst_api
    assert await auth.get_token(_DEVICE) == _token(_NOW + 600)
    assert api.requests == [
        (
            "Bearer portal-token",
            {
                "acl": [
                    {
                        "policy": [
                            {
                                "obj": ["Endpoint:eyfj07:device-id"],
                                "perms": ["Control"],
                            }
                        ],
                        "svc": "dim",
                    }
                ],
                "exp": 600,
                "sub": "user-id",
            },
        )
    ]
    assert await auth.get_token(_DEVICE) == _token(_NOW + 600)
    assert len(api.requests) == 1


async def test_concurrent_get_token(
    sst_api: tuple[SstAuthenticator, _SstApi],
) -> None:
    auth, api = sst_api
    first, second = await asyncio.gather(
        auth.get_token(_DEVICE),
        auth.get_token(_DEVICE),
    )
    assert first == second == _token(_NOW + 600)
    assert len(api.requests) == 1


@pytest.mark.parametrize(
    "other",
    [
        {**_DEVICE, "class": "other-class"},
        {**_DEVICE, "did": "other-device"},
        {**_DEVICE, "resource": "other-resource"},
    ],
)
async def test_device_cache_isolation(
    sst_api: tuple[SstAuthenticator, _SstApi], other: ApiDeviceInfo
) -> None:
    auth, api = sst_api
    await auth.get_token(_DEVICE)
    api.body = orjson.dumps(_response(_token(_NOW + 900)))
    assert await auth.get_token(other) == _token(_NOW + 900)
    assert await auth.get_token(_DEVICE) == _token(_NOW + 600)
    assert len(api.requests) == 2


async def test_force_refresh(sst_api: tuple[SstAuthenticator, _SstApi]) -> None:
    auth, api = sst_api
    await auth.get_token(_DEVICE)
    api.body = orjson.dumps(_response(_token(_NOW + 900)))
    assert await auth.get_token(_DEVICE, force=True) == _token(_NOW + 900)
    assert len(api.requests) == 2


async def test_invalidate(sst_api: tuple[SstAuthenticator, _SstApi]) -> None:
    auth, api = sst_api
    other: ApiDeviceInfo = {**_DEVICE, "did": "other-device"}
    await auth.get_token(_DEVICE)
    await auth.get_token(other)
    await auth.invalidate(_DEVICE)
    api.body = orjson.dumps(_response(_token(_NOW + 900)))
    assert await auth.get_token(_DEVICE) == _token(_NOW + 900)
    assert await auth.get_token(other) == _token(_NOW + 600)
    assert len(api.requests) == 3


@pytest.mark.parametrize("sst", [True, False])
async def test_refresh_before_expiry(
    sst_api: tuple[SstAuthenticator, _SstApi], sst: bool
) -> None:
    auth, api = sst_api
    api.body = orjson.dumps(_response(_token(_NOW + 600, sst=sst)))
    await auth.get_token(_DEVICE)
    api.body = orjson.dumps(_response(_token(_NOW + 900)))
    with patch("deebot_client.sst_authentication.time.time", return_value=_NOW + 539):
        assert await auth.get_token(_DEVICE) == _token(_NOW + 600, sst=sst)
    with patch("deebot_client.sst_authentication.time.time", return_value=_NOW + 540):
        assert await auth.get_token(_DEVICE) == _token(_NOW + 900)
    assert len(api.requests) == 2


@pytest.mark.parametrize(
    "token",
    [
        "opaque",
        "SST.header.invalid.signature",
        "SST.header.W10.signature",  # Decodes to a JSON list.
        "SST.header.e30.signature",  # Decodes to an empty JSON object.
    ],
)
async def test_fallback_expiry(
    sst_api: tuple[SstAuthenticator, _SstApi], token: str
) -> None:
    auth, api = sst_api
    api.body = orjson.dumps(_response(token))
    assert await auth.get_token(_DEVICE) == token
    api.body = orjson.dumps(_response(_token(_NOW + 900)))
    with patch("deebot_client.sst_authentication.time.time", return_value=_NOW + 479):
        assert await auth.get_token(_DEVICE) == token
    with patch("deebot_client.sst_authentication.time.time", return_value=_NOW + 480):
        assert await auth.get_token(_DEVICE) == _token(_NOW + 900)
    assert len(api.requests) == 2


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b"[]",
        b'{"code": 1}',
        b'{"code": 0}',
        b'{"code": 0, "data": null}',
        orjson.dumps(_response("")),
        b'{"code": 0, "data": {"data": {"token": 123}}}',
        orjson.dumps(_response(_token(_NOW - 1))),
    ],
)
async def test_invalid_response(
    sst_api: tuple[SstAuthenticator, _SstApi], body: bytes
) -> None:
    auth, api = sst_api
    api.body = body
    with pytest.raises(AuthenticationError):
        await auth.get_token(_DEVICE)
    api.body = orjson.dumps(_response(_token(_NOW + 600)))
    assert await auth.get_token(_DEVICE) == _token(_NOW + 600)
    assert len(api.requests) == 2


async def test_string_success_code(sst_api: tuple[SstAuthenticator, _SstApi]) -> None:
    auth, api = sst_api
    api.body = orjson.dumps({**_response(_token(_NOW + 600)), "code": "0000"})
    assert await auth.get_token(_DEVICE) == _token(_NOW + 600)


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (HTTPStatus.UNAUTHORIZED, AuthenticationError),
        (HTTPStatus.FORBIDDEN, AuthenticationError),
        (HTTPStatus.BAD_GATEWAY, ApiError),
    ],
)
async def test_http_errors(
    sst_api: tuple[SstAuthenticator, _SstApi], status: int, error: type[Exception]
) -> None:
    auth, api = sst_api
    api.status = status
    with pytest.raises(error):
        await auth.get_token(_DEVICE)


@pytest.mark.parametrize(
    ("cause", "error"),
    [(TimeoutError, ApiTimeoutError), (ClientConnectionError, ApiError)],
)
async def test_transport_errors(cause: type[Exception], error: type[Exception]) -> None:
    session = Mock(spec=ClientSession)
    session.post.side_effect = cause
    authenticator = Mock()
    authenticator.authenticate = AsyncMock(
        return_value=Credentials("portal-token", "user-id")
    )
    auth = SstAuthenticator(session, authenticator, base_url="https://example.invalid")
    with pytest.raises(error):
        await auth.get_token(_DEVICE)
