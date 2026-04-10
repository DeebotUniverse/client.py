from __future__ import annotations

from collections.abc import Mapping
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import ClientResponseError, RequestInfo
from multidict import CIMultiDictProxy, CIMultiDict
from yarl import URL

from deebot_client.exceptions import ApiError
from deebot_client.ngiot_client import NgiotClient, NgiotDeviceIdentity


def _request_info() -> RequestInfo:
    return RequestInfo(
        url=URL("https://api.example.com/api/iot/endpoint/control"),
        method="POST",
        headers=CIMultiDictProxy(CIMultiDict()),
        real_url=URL("https://api.example.com/api/iot/endpoint/control"),
    )


@pytest.fixture
def sst_authenticator() -> AsyncMock:
    auth = AsyncMock()
    auth.get_token.return_value = "sst-token"
    return auth


@pytest.fixture
def ngiot_client(sst_authenticator: AsyncMock) -> NgiotClient:
    return NgiotClient(Mock(), sst_authenticator)


def test_normalize_device_uses_override_host_and_keeps_service_host_as_fallback(
    ngiot_client: NgiotClient,
) -> None:
    ngiot_client._override_control_host = "override.example.com"

    identity = ngiot_client._normalize_device(
        {
            "did": "did-1",
            "class": "eyfj07",
            "resource": "res-1",
            "service": {"mqs": "service.example.com"},
        }
    )

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
            {
                "did": "did-1",
                "class": "eyfj07",
                "resource": "res-1",
            }
        )


@pytest.mark.parametrize(
    ("apn", "body_data", "expected"),
    [
        (
            "10001",
            {"fields": ["battery"]},
            {"fields": ["battery"], "type": "get"},
        ),
        (
            "30001",
            {"fields": ["mapData"]},
            {"fields": ["mapData"], "mapId": "0"},
        ),
    ],
    ids=["robot-detail", "map-details"],
)
def test_build_payload_adds_ngiot_defaults(
    ngiot_client: NgiotClient,
    apn: str,
    body_data: dict[str, object],
    expected: dict[str, object],
) -> None:
    payload = ngiot_client._build_payload(apn, body_data)

    assert isinstance(payload, Mapping)
    assert payload["reqId"]
    assert payload["timestamp"]
    for key, value in expected.items():
        assert payload[key] == value


@pytest.mark.asyncio
async def test_request_with_fallback_retries_on_404() -> None:
    client = NgiotClient(Mock(), AsyncMock())
    identity = NgiotDeviceIdentity(
        did="did-1",
        class_id="eyfj07",
        resource="res-1",
        control_host="api.example.com",
        fallback_control_host="service.example.com",
    )
    response_error = ClientResponseError(
        request_info=_request_info(),
        history=(),
        status=404,
        message="not found",
    )
    client._request_once = AsyncMock(
        side_effect=[response_error, {"body": {"code": 0, "data": {"ok": True}}}]
    )

    response = await client._request_with_fallback(
        identity,
        {"did": "did-1", "class": "eyfj07", "resource": "res-1"},
        apn="30001",
        body_data={"fields": ["mapData"]},
        fmt="j",
        ct="q",
        force_sst_refresh=False,
    )

    assert response == {"body": {"code": 0, "data": {"ok": True}}}
    assert client._request_once.await_count == 2
    first_identity = client._request_once.await_args_list[0].args[0]
    second_identity = client._request_once.await_args_list[1].args[0]
    assert first_identity.control_host == "api.example.com"
    assert second_identity.control_host == "service.example.com"
    assert second_identity.fallback_control_host is None


@pytest.mark.parametrize(
    ("response", "should_raise"),
    [
        ({"body": {"code": 0}}, False),
        ({"body": {"code": "0000"}}, False),
        ({"body": {"code": None}}, False),
        ({"body": {"code": 500, "msg": "fail"}}, True),
        ({}, True),
    ],
)
def test_validate_response(response: dict[str, object], should_raise: bool) -> None:
    if should_raise:
        with pytest.raises(ApiError):
            NgiotClient._validate_response(response)
    else:
        NgiotClient._validate_response(response)
