from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Self, cast
from unittest.mock import AsyncMock, Mock, patch

from aiohttp import ClientResponseError, ClientSession, RequestInfo, hdrs
from multidict import CIMultiDict, CIMultiDictProxy
import orjson
import pytest
from yarl import URL

from deebot_client.exceptions import ApiError, AuthenticationError
from deebot_client.ngiot_client import (
    NgiotClient,
    NgiotClientConfiguration,
    NgiotDeviceIdentity,
    NgiotRequest,
)

if TYPE_CHECKING:
    from deebot_client.models import ApiDeviceInfo


def _request_info() -> RequestInfo:
    return RequestInfo(
        url=URL("https://api.example.com/api/iot/endpoint/control"),
        method="POST",
        headers=CIMultiDictProxy(CIMultiDict()),
        real_url=URL("https://api.example.com/api/iot/endpoint/control"),
    )


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
        params: dict[str, str],
        data: bytes,
        headers: dict[str, str],
        timeout: object,
    ) -> _FakeResponse:
        self.post_calls.append(
            {
                "url": url,
                "params": params,
                "data": data,
                "headers": CIMultiDict(headers),
                "timeout": timeout,
            }
        )
        return self._responses.pop(0)


@pytest.fixture
def sst_authenticator() -> AsyncMock:
    authenticator = AsyncMock()
    authenticator.get_token.return_value = "sst-token"
    return authenticator


@pytest.fixture
def ngiot_client(sst_authenticator: AsyncMock) -> NgiotClient:
    return NgiotClient(cast("ClientSession", Mock()), sst_authenticator)


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
            "service": {"mqs": "service.example.com"},
        },
    )


def test_normalize_device_uses_override_host_and_keeps_service_host_as_fallback(
    sst_authenticator: AsyncMock,
    api_device: ApiDeviceInfo,
) -> None:
    client = NgiotClient(
        cast("ClientSession", Mock()),
        sst_authenticator,
        NgiotClientConfiguration(override_control_host="override.example.com"),
    )

    identity = client._normalize_device(api_device)

    assert identity == NgiotDeviceIdentity(
        did="did-1",
        class_id="eyfj07",
        resource="res-1",
        control_host="override.example.com",
        fallback_control_host="service.example.com",
    )
    assert identity.base_url == "https://override.example.com"


def test_normalize_device_requires_control_host(ngiot_client: NgiotClient) -> None:
    with pytest.raises(ApiError, match="Missing NGIOT control host"):
        ngiot_client._normalize_device(
            cast(
                "ApiDeviceInfo",
                {
                    "did": "did-1",
                    "class": "eyfj07",
                    "company": "eco",
                    "name": "robot",
                    "resource": "res-1",
                },
            )
        )


def test_normalize_device_requires_core_identity_fields(
    ngiot_client: NgiotClient,
) -> None:
    with pytest.raises(ApiError, match="Missing required NGIOT device field"):
        ngiot_client._normalize_device(
            cast(
                "ApiDeviceInfo",
                {
                    "did": "did-1",
                    "company": "eco",
                    "name": "robot",
                    "resource": "res-1",
                    "service": {"mqs": "service.example.com"},
                },
            )
        )


def test_build_payload_does_not_add_command_specific_defaults(
    ngiot_client: NgiotClient,
) -> None:
    payload = ngiot_client._build_payload({"fields": ["battery"]})

    assert isinstance(payload, Mapping)
    assert payload == {"fields": ["battery"]}


async def test_request_posts_endpoint_control_payload_and_returns_response_data(
    sst_authenticator: AsyncMock,
    api_device: ApiDeviceInfo,
) -> None:
    session = _FakeSession(
        [_FakeResponse({"body": {"code": 0, "data": {"battery": 100}}})]
    )
    client = NgiotClient(
        cast("ClientSession", session),
        sst_authenticator,
        NgiotClientConfiguration(
            user_agent="test-agent",
            channel="Android",
            protocol_version="0.0.22",
            timezone_name="Australia/Brisbane",
            timezone_offset_minutes=600,
        ),
    )

    response = await client.request(
        api_device,
        NgiotRequest(apn="10001", body_data={"fields": ["battery"]}),
    )

    assert response == {"body": {"code": 0, "data": {"battery": 100}}}
    assert len(session.post_calls) == 1
    call = session.post_calls[0]
    assert call["url"] == "https://service.example.com/api/iot/endpoint/control"
    assert call["params"] == {
        "si": call["params"]["si"],
        "ct": "q",
        "eid": "did-1",
        "et": "eyfj07",
        "er": "res-1",
        "apn": "10001",
        "fmt": "j",
    }
    assert len(call["params"]["si"]) == 32
    assert call["headers"][hdrs.AUTHORIZATION] == "Bearer sst-token"
    assert call["headers"][hdrs.CONTENT_TYPE] == "application/octet-stream"
    assert call["headers"][hdrs.USER_AGENT] == "test-agent"

    payload = orjson.loads(call["data"])
    assert payload["body"] == {"data": {"fields": ["battery"]}}
    assert payload["header"]["channel"] == "Android"
    assert payload["header"]["m"] == "request"
    assert payload["header"]["pri"] == 2
    assert payload["header"]["reqid"]
    assert payload["header"]["ts"]
    assert payload["header"]["tzc"] == "Australia/Brisbane"
    assert payload["header"]["tzm"] == 600
    assert payload["header"]["ver"] == "0.0.22"

    sst_authenticator.get_token.assert_awaited_once_with(
        {
            "did": "did-1",
            "class": "eyfj07",
            "resource": "res-1",
            "service": {"mqs": "service.example.com"},
        },
        force=False,
    )


async def test_query_fields_adds_fields_and_optional_map_id(
    sst_authenticator: AsyncMock,
    api_device: ApiDeviceInfo,
) -> None:
    session = _FakeSession([_FakeResponse({"body": {"code": 0, "data": {"ok": True}}})])
    client = NgiotClient(cast("ClientSession", session), sst_authenticator)

    response = await client.query_fields(
        api_device,
        apn="30001",
        fields=["mapData"],
        map_id="2",
    )

    assert response == {"ok": True}
    payload = orjson.loads(session.post_calls[0]["data"])
    assert payload["body"]["data"] == {"fields": ["mapData"], "mapId": "2"}
    assert session.post_calls[0]["params"]["apn"] == "30001"


async def test_write_data_sends_direct_mapping_payload(
    sst_authenticator: AsyncMock,
    api_device: ApiDeviceInfo,
) -> None:
    session = _FakeSession([_FakeResponse({"body": {"code": 0}})])
    client = NgiotClient(cast("ClientSession", session), sst_authenticator)

    response = await client.write_data(
        api_device,
        apn="40009",
        data={"pauseSwitch": True},
    )

    assert response == {}
    payload = orjson.loads(session.post_calls[0]["data"])
    assert payload["body"]["data"] == {"pauseSwitch": True}
    assert session.post_calls[0]["params"]["apn"] == "40009"


async def test_request_with_fallback_retries_on_404(
    sst_authenticator: AsyncMock,
    api_device: ApiDeviceInfo,
) -> None:
    session = _FakeSession(
        [
            _FakeResponse({}, status=HTTPStatus.NOT_FOUND),
            _FakeResponse({"body": {"code": 0, "data": {"ok": True}}}),
        ]
    )
    client = NgiotClient(
        cast("ClientSession", session),
        sst_authenticator,
        NgiotClientConfiguration(override_control_host="api.example.com"),
    )

    response = await client.request(
        api_device,
        NgiotRequest(apn="30001", body_data={"fields": ["mapData"]}),
    )

    assert response == {"body": {"code": 0, "data": {"ok": True}}}
    assert [call["url"] for call in session.post_calls] == [
        "https://api.example.com/api/iot/endpoint/control",
        "https://service.example.com/api/iot/endpoint/control",
    ]


async def test_request_invalidates_sst_and_retries_once_after_unauthorized(
    sst_authenticator: AsyncMock,
    api_device: ApiDeviceInfo,
) -> None:
    session = _FakeSession(
        [
            _FakeResponse({}, status=HTTPStatus.UNAUTHORIZED),
            _FakeResponse({"body": {"code": 0, "data": {"ok": True}}}),
        ]
    )
    client = NgiotClient(cast("ClientSession", session), sst_authenticator)

    response = await client.request(
        api_device,
        NgiotRequest(apn="10001", body_data={"fields": ["battery"]}),
    )

    assert response == {"body": {"code": 0, "data": {"ok": True}}}
    assert len(session.post_calls) == 2
    assert sst_authenticator.invalidate.await_count == 1
    assert sst_authenticator.get_token.await_args_list[0].kwargs == {"force": False}
    assert sst_authenticator.get_token.await_args_list[1].kwargs == {"force": True}


async def test_request_raises_authentication_error_after_second_unauthorized(
    sst_authenticator: AsyncMock,
    api_device: ApiDeviceInfo,
) -> None:
    session = _FakeSession(
        [
            _FakeResponse({}, status=HTTPStatus.UNAUTHORIZED),
            _FakeResponse({}, status=HTTPStatus.UNAUTHORIZED),
        ]
    )
    client = NgiotClient(cast("ClientSession", session), sst_authenticator)

    with pytest.raises(AuthenticationError):
        await client.request(
            api_device,
            NgiotRequest(apn="10001", body_data={"fields": ["battery"]}),
        )

    assert len(session.post_calls) == 2
    assert sst_authenticator.invalidate.await_count == 1


async def test_request_retries_transient_busy_once(
    sst_authenticator: AsyncMock,
    api_device: ApiDeviceInfo,
) -> None:
    session = _FakeSession(
        [
            _FakeResponse({"body": {"code": 1, "msg": "cmd busy"}}),
            _FakeResponse({"body": {"code": 0, "data": {"ok": True}}}),
        ]
    )
    client = NgiotClient(cast("ClientSession", session), sst_authenticator)

    with patch("deebot_client.ngiot_client.asyncio.sleep", new=AsyncMock()):
        response = await client.request(
            api_device,
            NgiotRequest(apn="10001", body_data={"fields": ["battery"]}),
        )

    assert response == {"body": {"code": 0, "data": {"ok": True}}}
    assert len(session.post_calls) == 2


@pytest.mark.parametrize(
    ("response", "classification"),
    [
        ({"body": {"code": 0}}, "ok"),
        ({"body": {"code": "0000"}}, "ok"),
        ({"body": {"code": None}}, "ok"),
        ({"body": {"code": 1, "msg": "cmd busy"}}, "retry_busy"),
        ({}, "ok"),
    ],
)
def test_classify_response(
    response: dict[str, object],
    classification: str,
) -> None:
    assert NgiotClient._classify_response(response) == classification


@pytest.mark.parametrize(
    "response",
    [
        {"body": {"code": 500, "msg": "fail"}},
        {"body": "invalid"},
        {},
    ],
)
def test_validate_response_raises_on_invalid_response(
    response: dict[str, object],
) -> None:
    with pytest.raises(ApiError):
        NgiotClient._validate_response(response)
