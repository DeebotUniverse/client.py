"""Tests for the live view."""

from __future__ import annotations

import hashlib
from typing import Any, Self
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import parse_qs, urlparse

import orjson
import pytest

from deebot_client.authentication import Authenticator, create_rest_config
from deebot_client.device import Device
from deebot_client.hardware import get_static_device_info
from deebot_client.live_view import (
    LiveViewError,
    LiveViewPinError,
    LiveViewSource,
    PinEncoding,
    async_get_live_view_source,
    encode_pin,
)
from deebot_client.models import ApiDeviceInfo, Credentials, DeviceInfo

_DEVICE_INFO = ApiDeviceInfo(
    {  # type: ignore[typeddict-item]
        "did": "did-1",
        "class": "2px96q",
        "resource": "res",
        "service": {"mqs": "api-ngiot.dc-eu.ww.ecouser.net"},
    }
)
_WATCH_OK = {
    "ret": "ok",
    "region": "eu-central-1",
    "channel": "production-user",
    "client_id": "viewer-1",
    "session": "s",
    "credentials": {
        "AccessKeyId": "AKID",
        "SecretAccessKey": "secret",
        "SessionToken": "token",
    },
}


class _Response:
    def __init__(self, data: Any, status: int = 200) -> None:
        self.status = status
        self._data = data

    async def read(self) -> bytes:
        return orjson.dumps(self._data)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class _Session:
    """Fake aiohttp session, which records the requests."""

    def __init__(
        self,
        watch: Any,
        overrides: dict[str, _Response] | None = None,
    ) -> None:
        self.requests: list[tuple[str, str, dict[str, Any]]] = []
        self._watch = watch
        self._overrides = overrides or {}

    def get(self, url: str, **kwargs: Any) -> _Response:
        self.requests.append(("GET", url, kwargs))
        return _Response(self._watch)

    def post(self, url: str, **kwargs: Any) -> _Response:
        self.requests.append(("POST", url, kwargs))
        if response := self._overrides.get(url.rsplit("/", 1)[-1]):
            return response
        if url.endswith("/describeSignalingChannel"):
            return _Response({"ChannelInfo": {"ChannelARN": "arn:channel"}})
        if url.endswith("/getSignalingChannelEndpoint"):
            return _Response(
                {
                    "ResourceEndpointList": [
                        {"Protocol": "WSS", "ResourceEndpoint": "wss://v-1.kvs"},
                        {"Protocol": "HTTPS", "ResourceEndpoint": "https://r-1.kvs"},
                    ]
                }
            )
        if url.endswith("/v1/get-ice-server-config"):
            return _Response(
                {
                    "IceServerList": [
                        {"Uris": ["turn:1.2.3.4:443"], "Username": "u", "Password": "p"}
                    ]
                }
            )
        return _Response({})  # appping


def _authenticator(session: _Session) -> Mock:
    authenticator = Mock(spec_set=Authenticator)
    authenticator.config = create_rest_config(
        session,  # type: ignore[arg-type]
        device_id="CLIENT01",
        alpha_2_country="DE",
    )
    authenticator.authenticate = AsyncMock(
        return_value=Credentials("ecotoken", "user-1", 0)
    )
    return authenticator


@pytest.mark.parametrize(
    ("encoding", "expected"),
    [
        (PinEncoding.GOAT_MD5, hashlib.md5(b"goat_1234").hexdigest()),  # noqa: S324
        (PinEncoding.GOAT_SHA256, hashlib.sha256(b"goat_1234").hexdigest()),
        (PinEncoding.ECO_MD5, hashlib.md5(b"eco_1234").hexdigest()),  # noqa: S324
    ],
)
def test_encode_pin(encoding: PinEncoding, expected: str) -> None:
    assert encode_pin("1234", encoding) == expected


async def test_live_view_source() -> None:
    session = _Session(_WATCH_OK)
    source = await async_get_live_view_source(
        _authenticator(session), _DEVICE_INFO, "1234", PinEncoding.GOAT_MD5
    )

    method, url, kwargs = session.requests[0]
    assert method == "GET"
    assert url == "https://portal-eu.ecouser.net/api/appsvr/akvs/start_watch/v2"
    assert kwargs["params"]["pwd"] == hashlib.md5(b"goat_1234").hexdigest()  # noqa: S324
    assert kwargs["params"]["did"] == "did-1"
    assert orjson.loads(kwargs["params"]["auth"])["resource"] == "CLIENT01"
    assert [r[1].rsplit("/", 1)[-1] for r in session.requests[1:]] == [
        "control",
        "describeSignalingChannel",
        "getSignalingChannelEndpoint",
        "get-ice-server-config",
    ]
    assert (
        "AWS4-HMAC-SHA256 Credential=AKID/"
        in (session.requests[2][2]["headers"]["Authorization"])
    )

    url_part, *fragments = source.url.split("#")
    assert url_part.startswith("webrtc:wss://v-1.kvs/?")
    query = parse_qs(urlparse(url_part.removeprefix("webrtc:")).query)
    assert query["X-Amz-ChannelARN"] == ["arn:channel"]
    assert query["X-Amz-ClientId"] == ["viewer-1"]
    assert query["X-Amz-Security-Token"] == ["token"]
    assert "X-Amz-Signature" in query
    assert fragments[0] == "format=kinesis"
    assert fragments[1] == "client_id=viewer-1"
    ice = orjson.loads(fragments[2].removeprefix("ice_servers="))
    assert ice[0] == {"urls": ["stun:stun.kinesisvideo.eu-central-1.amazonaws.com:443"]}
    assert ice[1] == {"urls": ["turn:1.2.3.4:443"], "username": "u", "credential": "p"}


@pytest.mark.parametrize(
    ("watch", "error"),
    [
        (
            {"ret": "fail", "code": 30010, "message": "live launch pwd check fail"},
            LiveViewPinError,
        ),
        ({"ret": "fail", "code": 1, "message": "other"}, LiveViewError),
    ],
)
async def test_live_view_errors(watch: dict[str, Any], error: type[Exception]) -> None:
    session = _Session(watch)
    with pytest.raises(error):
        await async_get_live_view_source(
            _authenticator(session), _DEVICE_INFO, "1234", PinEncoding.GOAT_MD5
        )
    assert len(session.requests) == 1


async def test_live_view_invalid_start_watch_response() -> None:
    session = _Session(["unexpected"])
    with pytest.raises(LiveViewError, match="invalid response"):
        await async_get_live_view_source(
            _authenticator(session), _DEVICE_INFO, "1234", PinEncoding.GOAT_MD5
        )


async def test_live_view_without_mqs_skips_app_ping() -> None:
    session = _Session(_WATCH_OK)
    device_info = ApiDeviceInfo(
        {"did": "did-1", "class": "2px96q", "resource": "res"}  # type: ignore[typeddict-item]
    )
    source = await async_get_live_view_source(
        _authenticator(session), device_info, "1234", PinEncoding.GOAT_MD5
    )
    assert source.url.startswith("webrtc:wss://v-1.kvs/?")
    assert [r[1].rsplit("/", 1)[-1] for r in session.requests[1:]] == [
        "describeSignalingChannel",
        "getSignalingChannelEndpoint",
        "get-ice-server-config",
    ]


async def test_live_view_app_ping_error_is_ignored() -> None:
    session = _Session(_WATCH_OK, {"control": _Response({}, status=500)})
    source = await async_get_live_view_source(
        _authenticator(session), _DEVICE_INFO, "1234", PinEncoding.GOAT_MD5
    )
    assert source.url.startswith("webrtc:wss://v-1.kvs/?")


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        (
            {"describeSignalingChannel": _Response({}, status=403)},
            "failed with HTTP 403",
        ),
        (
            {"getSignalingChannelEndpoint": _Response(["unexpected"])},
            "invalid response",
        ),
    ],
)
async def test_live_view_aws_errors(
    overrides: dict[str, _Response], match: str
) -> None:
    session = _Session(_WATCH_OK, overrides)
    with pytest.raises(LiveViewError, match=match):
        await async_get_live_view_source(
            _authenticator(session), _DEVICE_INFO, "1234", PinEncoding.GOAT_MD5
        )


async def test_device_live_view(
    api_device_info: ApiDeviceInfo, authenticator: Authenticator
) -> None:
    static = await get_static_device_info("2px96q")
    assert static
    device = Device(DeviceInfo(api_device_info, static), authenticator)
    source = LiveViewSource(url="webrtc:wss://x", created=0)
    with patch(
        "deebot_client.device.async_get_live_view_source",
        AsyncMock(return_value=source),
    ) as mock_get:
        assert await device.async_get_live_view_source("1234") is source
    mock_get.assert_awaited_once_with(
        authenticator, device.device_info, "1234", PinEncoding.GOAT_MD5
    )


async def test_device_live_view_not_supported(
    api_device_info: ApiDeviceInfo, authenticator: Authenticator
) -> None:
    static = await get_static_device_info("yna5xi")
    assert static
    device = Device(DeviceInfo(api_device_info, static), authenticator)
    with pytest.raises(LiveViewError, match="not supported"):
        await device.async_get_live_view_source("1234")


def test_authenticator_config() -> None:
    config = create_rest_config(
        Mock(),
        device_id="CLIENT01",
        alpha_2_country="DE",
    )
    assert Authenticator(config, "account", "hash").config is config
