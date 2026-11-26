from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, Mock

from aiohttp import (
    ClientConnectionError,
    ClientResponse,
    ClientResponseError,
    ClientSession,
    hdrs,
)
import orjson
import pytest

from deebot_client.exceptions import ApiError, ApiTimeoutError, AuthenticationError
from deebot_client.models import ApiDeviceInfo, Credentials
from deebot_client.ngiot_client import NgiotClient

if TYPE_CHECKING:
    from collections.abc import Mapping


@pytest.fixture
def ngiot_device() -> ApiDeviceInfo:
    return {
        "company": "eco-ng",
        "did": "device-id",
        "class": "eyfj07",
        "name": "NEO 2.0",
        "resource": "resource-id",
        "service": {"mqs": "api-ngiot.dc-na.ww.ecouser.net"},
    }


@pytest.fixture
def ngiot_session() -> Mock:
    session = Mock(spec_set=ClientSession)
    session.post.return_value = MagicMock()
    response = Mock(spec_set=ClientResponse)
    session.post.return_value.__aenter__.return_value = response
    response.status = HTTPStatus.OK
    response.json = AsyncMock(return_value={"body": {"code": 0}})
    return session


@pytest.mark.parametrize(
    ("apn", "data", "result"),
    [
        (
            "10001",
            {"fields": ["battery"]},
            {"body": {"code": 0, "data": {"battery": 90}}},
        ),
        ("40009", {"pauseSwitch": True}, {"body": {"code": 0, "msg": "ok"}}),
        ("10001", ["battery"], {"body": {"code": 1, "msg": "cmd busy"}}),
    ],
)
async def test_request(
    ngiot_session: Mock,
    ngiot_device: ApiDeviceInfo,
    apn: str,
    data: dict[str, Any] | list[Any],
    result: dict[str, Any],
) -> None:
    response = ngiot_session.post.return_value.__aenter__.return_value
    response.json.return_value = result
    client = NgiotClient(ngiot_session)
    credentials = Credentials("portal-token", "user-id")
    assert await client.request(credentials, ngiot_device, apn, data) == result

    ngiot_session.post.assert_called_once()
    args, kwargs = ngiot_session.post.call_args
    assert args == ("https://api-ngiot.dc-na.ww.ecouser.net/api/iot/endpoint/control",)
    params = kwargs["params"]
    request_id = params["si"]
    assert len(request_id) == 16
    assert params == {
        "si": request_id,
        "ct": "q",
        "eid": "device-id",
        "et": "eyfj07",
        "er": "resource-id",
        "apn": apn,
        "fmt": "j",
    }
    headers: Mapping[str, str] = kwargs["headers"]
    assert headers[hdrs.AUTHORIZATION] == f"Bearer {credentials.token}"
    assert headers[hdrs.CONTENT_TYPE] == "application/octet-stream"
    assert headers["x-eco-request-id"] == request_id
    assert headers[hdrs.USER_AGENT] == "EcovacsHome/287541 CFNetwork Darwin"
    assert kwargs["timeout"].total == 60
    assert kwargs["allow_redirects"] is False
    payload = orjson.loads(kwargs["data"])
    assert payload["body"] == {"data": data}
    header = payload["header"]
    assert header == {
        "channel": "iOS",
        "m": "request",
        "pri": 1,
        "reqid": header["reqid"],
        "ts": header["ts"],
        "tzc": "UTC",
        "tzm": 0,
        "ver": "0.0.50",
    }
    assert len(header["reqid"]) == 6
    assert header["ts"].isdigit()
    assert "auth" not in payload
    response.json.assert_awaited_once_with(content_type=None, loads=orjson.loads)


@pytest.mark.parametrize(
    "host",
    [
        None,
        "",
        "example.com",
        "api-ngiot.dc-na.ww.ecouser.net.evil.test",
        "http://api-ngiot.dc-na.ww.ecouser.net",
        "api-ngiot.dc-na.ww.ecouser.net@evil.test",
    ],
)
async def test_reject_invalid_host(
    ngiot_session: Mock, ngiot_device: ApiDeviceInfo, host: str | None
) -> None:
    if host is None:
        ngiot_device.pop("service")
    else:
        ngiot_device["service"] = {"mqs": host}
    with pytest.raises(ApiError, match="NGIOT control host"):
        await NgiotClient(ngiot_session).request(
            Credentials("portal-token", "user-id"), ngiot_device, "10001", {}
        )
    ngiot_session.post.assert_not_called()


@pytest.mark.parametrize("status", [401, 403, 404, 500, 502])
async def test_http_error_is_not_retried(
    ngiot_session: Mock, ngiot_device: ApiDeviceInfo, status: int
) -> None:
    response = ngiot_session.post.return_value.__aenter__.return_value
    response.raise_for_status.side_effect = ClientResponseError(
        Mock(), (), status=status
    )
    expected = AuthenticationError if status in (401, 403) else ApiError
    with pytest.raises(expected):
        await NgiotClient(ngiot_session).request(
            Credentials("portal-token", "user-id"),
            ngiot_device,
            "40009",
            {"pauseSwitch": True},
        )
    ngiot_session.post.assert_called_once()


@pytest.mark.parametrize("status", [204, 302])
async def test_unexpected_status(
    ngiot_session: Mock, ngiot_device: ApiDeviceInfo, status: int
) -> None:
    response = ngiot_session.post.return_value.__aenter__.return_value
    response.status = status
    with pytest.raises(ApiError, match="HTTP status"):
        await NgiotClient(ngiot_session).request(
            Credentials("portal-token", "user-id"), ngiot_device, "10001", {}
        )
    response.json.assert_not_awaited()
    ngiot_session.post.assert_called_once()


@pytest.mark.parametrize(
    "result",
    [
        None,
        [],
        {},
        {"body": []},
        {"body": {}},
        {"body": {"code": None}},
        {"body": {"code": False}},
    ],
)
async def test_invalid_response(
    ngiot_session: Mock, ngiot_device: ApiDeviceInfo, result: Any
) -> None:
    response = ngiot_session.post.return_value.__aenter__.return_value
    response.json.return_value = result
    with pytest.raises(ApiError, match="NGIOT response"):
        await NgiotClient(ngiot_session).request(
            Credentials("portal-token", "user-id"), ngiot_device, "10001", {}
        )


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError(), ApiTimeoutError),
        (ClientConnectionError(), ApiError),
        (ValueError(), ApiError),
    ],
)
async def test_request_failure(
    ngiot_session: Mock,
    ngiot_device: ApiDeviceInfo,
    error: Exception,
    expected: type[ApiError],
) -> None:
    response = ngiot_session.post.return_value.__aenter__.return_value
    response.json.side_effect = error
    with pytest.raises(expected):
        await NgiotClient(ngiot_session).request(
            Credentials("portal-token", "user-id"), ngiot_device, "10001", {}
        )
    ngiot_session.post.assert_called_once()


async def test_uses_device_service_host(
    ngiot_session: Mock, ngiot_device: ApiDeviceInfo
) -> None:
    ngiot_device["service"] = {"mqs": "api-ngiot.dc-eu.ww.ecouser.net"}
    await NgiotClient(ngiot_session).request(
        Credentials("portal-token", "user-id"), ngiot_device, "10001", {}
    )
    assert ngiot_session.post.call_args.args == (
        "https://api-ngiot.dc-eu.ww.ecouser.net/api/iot/endpoint/control",
    )
