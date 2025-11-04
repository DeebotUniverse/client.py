"""Test api_client module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest

from deebot_client.api_client import ApiClient, Devices
from deebot_client.const import (
    PATH_API_APPSVR_APP,
    PATH_API_PIM_PRODUCT_IOT_MAP,
    PATH_API_USERS_USER,
)
from deebot_client.exceptions import ApiError

if TYPE_CHECKING:
    from deebot_client.authentication import Authenticator


@pytest.fixture
def api_client_mock(authenticator: Authenticator) -> ApiClient:
    """Fixture for ApiClient with mock authenticator."""
    return ApiClient(authenticator)


async def test_get_devices_success(
    api_client_mock: ApiClient, authenticator: Authenticator
) -> None:
    """Test successful device retrieval."""
    device_data = {
        "did": "device1",
        "name": "Test Device",
        "nick": "My Robot",
        "class": "yna5xi",
        "resource": "resource1",
        "company": "eco-ng",
    }

    authenticator.post_authenticated.return_value = {"devices": [device_data]}

    devices = await api_client_mock.get_devices()

    assert isinstance(devices, Devices)
    assert len(devices.mqtt) == 1
    assert len(devices.xmpp) == 0
    assert len(devices.not_supported) == 0
    assert devices.mqtt[0].api["did"] == "device1"


async def test_get_devices_eco_legacy(
    api_client_mock: ApiClient, authenticator: Authenticator
) -> None:
    """Test device retrieval with eco-legacy devices."""
    device_data = {
        "did": "device1",
        "name": "Test Device",
        "nick": "My Robot",
        "class": "old_class",
        "resource": "resource1",
        "company": "eco-legacy",
    }

    authenticator.post_authenticated.return_value = {"devices": [device_data]}

    devices = await api_client_mock.get_devices()

    assert len(devices.mqtt) == 0
    assert len(devices.xmpp) == 1
    assert len(devices.not_supported) == 0
    assert devices.xmpp[0]["did"] == "device1"


async def test_get_devices_not_supported(
    api_client_mock: ApiClient, authenticator: Authenticator
) -> None:
    """Test device retrieval with unsupported devices."""
    device_data = {
        "did": "device1",
        "name": "Test Device",
        "nick": "My Robot",
        "class": "unknown_class",
        "resource": "resource1",
        "company": "unknown-company",
    }

    authenticator.post_authenticated.return_value = {"devices": [device_data]}

    devices = await api_client_mock.get_devices()

    assert len(devices.mqtt) == 0
    assert len(devices.xmpp) == 0
    assert len(devices.not_supported) == 1
    assert devices.not_supported[0]["did"] == "device1"


async def test_get_devices_unrecognized_class(
    api_client_mock: ApiClient, authenticator: Authenticator
) -> None:
    """Test device retrieval with unrecognized device class."""
    device_data = {
        "did": "device1",
        "name": "Test Device",
        "nick": "My Robot",
        "class": "unrecognized_class",
        "resource": "resource1",
        "company": "eco-ng",
    }

    authenticator.post_authenticated.return_value = {"devices": [device_data]}

    devices = await api_client_mock.get_devices()

    assert len(devices.mqtt) == 0
    assert len(devices.xmpp) == 0
    assert len(devices.not_supported) == 1


async def test_get_devices_no_devices(
    api_client_mock: ApiClient, authenticator: Authenticator, caplog: pytest.LogCaptureFixture
) -> None:
    """Test device retrieval with no devices returned."""
    authenticator.post_authenticated.return_value = {}

    devices = await api_client_mock.get_devices()

    assert len(devices.mqtt) == 0
    assert len(devices.xmpp) == 0
    assert len(devices.not_supported) == 0
    assert "No devices returned by the api" in caplog.text


async def test_get_devices_failed_response(
    api_client_mock: ApiClient, authenticator: Authenticator, caplog: pytest.LogCaptureFixture
) -> None:
    """Test device retrieval with failed response."""
    authenticator.post_authenticated.return_value = {"code": 500, "msg": "error"}

    devices = await api_client_mock.get_devices()

    assert len(devices.mqtt) == 0
    assert "Failed to get devices" in caplog.text


async def test_get_devices_api_error(
    api_client_mock: ApiClient, authenticator: Authenticator
) -> None:
    """Test device retrieval with API error."""
    authenticator.post_authenticated.side_effect = Exception("API Error")

    with pytest.raises(ApiError, match="Error on getting devices"):
        await api_client_mock.get_devices()


async def test_get_devices_merges_device_lists(
    api_client_mock: ApiClient, authenticator: Authenticator
) -> None:
    """Test that get_devices merges device lists from both endpoints."""
    device1 = {
        "did": "device1",
        "name": "Device 1",
        "nick": "Robot 1",
        "class": "yna5xi",
        "resource": "resource1",
        "company": "eco-ng",
    }
    device2 = {
        "did": "device2",
        "name": "Device 2",
        "nick": "Robot 2",
        "class": "yna5xi",
        "resource": "resource2",
        "company": "eco-ng",
    }

    def side_effect(path: str, json: dict[str, Any]) -> dict[str, Any]:
        if path == PATH_API_USERS_USER:
            return {"devices": [device1]}
        if path == PATH_API_APPSVR_APP:
            return {"devices": [device2]}
        return {}

    authenticator.post_authenticated.side_effect = side_effect

    devices = await api_client_mock.get_devices()

    assert len(devices.mqtt) == 2


async def test_get_product_iot_map_success(
    api_client_mock: ApiClient, authenticator: Authenticator
) -> None:
    """Test successful product IoT map retrieval."""
    response = {
        "code": 0,
        "data": [
            {"classid": "class1", "product": {"name": "Product 1"}},
            {"classid": "class2", "product": {"name": "Product 2"}},
        ],
    }

    authenticator.post_authenticated.return_value = response

    result = await api_client_mock.get_product_iot_map()

    assert "class1" in result
    assert "class2" in result
    assert result["class1"]["name"] == "Product 1"
    assert result["class2"]["name"] == "Product 2"


async def test_get_product_iot_map_success_string_code(
    api_client_mock: ApiClient, authenticator: Authenticator
) -> None:
    """Test successful product IoT map retrieval with string code."""
    response = {
        "code": "0000",
        "data": [
            {"classid": "class1", "product": {"name": "Product 1"}},
        ],
    }

    authenticator.post_authenticated.return_value = response

    result = await api_client_mock.get_product_iot_map()

    assert "class1" in result


async def test_get_product_iot_map_error(
    api_client_mock: ApiClient, authenticator: Authenticator
) -> None:
    """Test product IoT map retrieval with error response."""
    response = {
        "code": 500,
        "error": "Internal Error",
        "errno": "E500",
    }

    authenticator.post_authenticated.return_value = response

    with pytest.raises(ApiError, match="failure Internal Error \\(E500\\)"):
        await api_client_mock.get_product_iot_map()
