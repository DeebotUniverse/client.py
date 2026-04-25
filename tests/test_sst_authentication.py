from __future__ import annotations

import base64
from http import HTTPStatus
import time
from typing import TYPE_CHECKING, Any, Self, cast
from unittest.mock import AsyncMock

from aiohttp import ClientResponseError, ClientSession, RequestInfo
from multidict import CIMultiDict, CIMultiDictProxy
import orjson
import pytest
from yarl import URL

from deebot_client.exceptions import ApiError, AuthenticationError
from deebot_client.models import ApiDeviceInfo, Credentials
from deebot_client.sst_authentication import (
    SstAuthenticator,
    SstCredentials,
    SstDeviceIdentity,
    identity_as_mapping,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


def _request_info() -> RequestInfo:
    return RequestInfo(
        url=URL("https://api-base.example.com/api/new-perm/token/sst/issue"),
        method="POST",
        headers=CIMultiDictProxy(CIMultiDict()),
        real_url=URL("https://api-base.example.com/api/new-perm/token/sst/issue"),
    )


def _token_with_exp(expires_at: int) -> str:
    header = base64.urlsafe_b64encode(orjson.dumps({"alg": "none"})).rstrip(b"=")
    payload = base64.urlsafe_b64encode(orjson.dumps({"exp": expires_at})).rstrip(b"=")
    return f"{header.decode()}.{payload.decode()}.signature"


class _FakeResponse:
    def __init__(self, body: Mapping[str, Any], *, status: int = HTTPStatus.OK) -> None:
        self._body = body
        self.status = status
        self.request_info = _request_info()
        self.history: tuple[()] = ()
        self.headers = CIMultiDictProxy(
            CIMultiDict({"content-type": "application/json"})
        )
        self.reason = "OK" if status == HTTPStatus.OK else "error"

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: object,
    ) -> None:
        pass

    def raise_for_status(self) -> None:
        if self.status >= HTTPStatus.BAD_REQUEST:
            raise ClientResponseError(
                request_info=self.request_info,
                history=self.history,
                status=self.status,
                message=self.reason,
                headers=self.headers,
            )

    async def read(self) -> bytes:
        return orjson.dumps(self._body)


class _FakeSession:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self._responses = responses
        self.post_calls: list[dict[str, Any]] = []

    def post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: object,
    ) -> _FakeResponse:
        self.post_calls.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return self._responses.pop(0)


@pytest.fixture
def api_device() -> ApiDeviceInfo:
    return cast(
        "ApiDeviceInfo",
        {
            "did": "did-1",
            "class": "eyfj07",
            "company": "eco",
            "name": "robot",
            "resource": "res-1",
        },
    )


@pytest.fixture
def authenticator() -> AsyncMock:
    auth = AsyncMock()
    auth.authenticate.return_value = Credentials(
        "account-token",
        "user-1",
        int(time.time()) + 3600,
    )
    return auth


def test_identity_endpoint_and_cache_key() -> None:
    identity = SstDeviceIdentity(did="did-1", class_id="eyfj07", resource="res-1")

    assert identity.endpoint == "Endpoint:eyfj07:did-1"
    assert identity.key == "eyfj07:did-1:res-1"
    assert identity_as_mapping(identity) == {
        "did": "did-1",
        "class": "eyfj07",
        "resource": "res-1",
    }


def test_decode_exp_supports_jwt_and_sst_prefixed_tokens() -> None:
    expires_at = int(time.time()) + 600
    jwt = _token_with_exp(expires_at)
    sst = f"SST.prefix.{jwt.split('.')[1]}.signature"

    assert SstAuthenticator._decode_exp(jwt) == expires_at
    assert SstAuthenticator._decode_exp(sst) == expires_at


async def test_get_credentials_issues_sst_and_uses_cache(
    authenticator: AsyncMock,
    api_device: ApiDeviceInfo,
) -> None:
    expires_at = int(time.time()) + 600
    token = _token_with_exp(expires_at)
    session = _FakeSession(
        [
            _FakeResponse(
                {"code": 0, "data": {"data": {"token": token}}},
            )
        ]
    )
    sst_authenticator = SstAuthenticator(
        cast("ClientSession", session),
        authenticator,
        base_url="https://api-base.example.com",
    )

    credentials = await sst_authenticator.get_credentials(api_device)
    cached_credentials = await sst_authenticator.get_credentials(api_device)

    assert credentials == SstCredentials(
        token=token,
        expires_at=expires_at,
        device_key="eyfj07:did-1:res-1",
    )
    assert cached_credentials == credentials
    assert len(session.post_calls) == 1
    assert session.post_calls[0]["url"] == (
        "https://api-base.example.com/api/new-perm/token/sst/issue"
    )
    assert session.post_calls[0]["headers"]["Authorization"] == "Bearer account-token"
    assert session.post_calls[0]["json"] == {
        "acl": [
            {
                "policy": [
                    {
                        "obj": ["Endpoint:eyfj07:did-1"],
                        "perms": ["Control"],
                    }
                ],
                "svc": "dim",
            }
        ],
        "exp": 600,
        "sub": "user-1",
    }
    authenticator.authenticate.assert_awaited_once()

    await sst_authenticator.teardown()


async def test_get_credentials_force_refresh_issues_new_token(
    authenticator: AsyncMock,
    api_device: ApiDeviceInfo,
) -> None:
    first_token = _token_with_exp(int(time.time()) + 600)
    second_token = _token_with_exp(int(time.time()) + 900)
    session = _FakeSession(
        [
            _FakeResponse({"code": 0, "data": {"data": {"token": first_token}}}),
            _FakeResponse({"code": 0, "data": {"data": {"token": second_token}}}),
        ]
    )
    sst_authenticator = SstAuthenticator(
        cast("ClientSession", session),
        authenticator,
        base_url="https://api-base.example.com",
    )

    first = await sst_authenticator.get_credentials(api_device)
    second = await sst_authenticator.get_credentials(api_device, force=True)

    assert first.token == first_token
    assert second.token == second_token
    assert len(session.post_calls) == 2

    await sst_authenticator.teardown()


async def test_invalidate_removes_cached_credentials(
    authenticator: AsyncMock,
    api_device: ApiDeviceInfo,
) -> None:
    token = _token_with_exp(int(time.time()) + 600)
    session = _FakeSession(
        [_FakeResponse({"code": 0, "data": {"data": {"token": token}}})]
    )
    sst_authenticator = SstAuthenticator(
        cast("ClientSession", session),
        authenticator,
        base_url="https://api-base.example.com",
    )

    credentials = await sst_authenticator.get_credentials(api_device)
    assert credentials.device_key in sst_authenticator._credentials

    await sst_authenticator.invalidate(api_device)

    assert credentials.device_key not in sst_authenticator._credentials
    assert credentials.device_key not in sst_authenticator._refresh_handles

    await sst_authenticator.teardown()


async def test_issue_sst_rejects_error_response(
    authenticator: AsyncMock,
    api_device: ApiDeviceInfo,
) -> None:
    session = _FakeSession([_FakeResponse({"code": 500, "msg": "failed"})])
    sst_authenticator = SstAuthenticator(
        cast("ClientSession", session),
        authenticator,
        base_url="https://api-base.example.com",
    )

    with pytest.raises(AuthenticationError, match="failure code 500"):
        await sst_authenticator.get_credentials(api_device)


async def test_issue_sst_rejects_missing_token(
    authenticator: AsyncMock,
    api_device: ApiDeviceInfo,
) -> None:
    session = _FakeSession([_FakeResponse({"code": 0, "data": {"data": {}}})])
    sst_authenticator = SstAuthenticator(
        cast("ClientSession", session),
        authenticator,
        base_url="https://api-base.example.com",
    )

    with pytest.raises(AuthenticationError, match="did not contain a token"):
        await sst_authenticator.get_credentials(api_device)


async def test_issue_sst_raises_authentication_error_on_unauthorized(
    authenticator: AsyncMock,
    api_device: ApiDeviceInfo,
) -> None:
    session = _FakeSession([_FakeResponse({}, status=HTTPStatus.UNAUTHORIZED)])
    sst_authenticator = SstAuthenticator(
        cast("ClientSession", session),
        authenticator,
        base_url="https://api-base.example.com",
    )

    with pytest.raises(AuthenticationError, match="not authorized"):
        await sst_authenticator.get_credentials(api_device)


async def test_issue_sst_raises_api_error_on_other_http_error(
    authenticator: AsyncMock,
    api_device: ApiDeviceInfo,
) -> None:
    session = _FakeSession([_FakeResponse({}, status=HTTPStatus.INTERNAL_SERVER_ERROR)])
    sst_authenticator = SstAuthenticator(
        cast("ClientSession", session),
        authenticator,
        base_url="https://api-base.example.com",
    )

    with pytest.raises(ApiError):
        await sst_authenticator.get_credentials(api_device)
