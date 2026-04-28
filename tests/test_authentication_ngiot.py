from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, patch

import pytest

from deebot_client.authentication import Authenticator, NgiotConfiguration
from deebot_client.commands.ngiot.battery import GetBattery
from deebot_client.const import DataType
from deebot_client.exceptions import ApiError
from deebot_client.models import ApiDeviceInfo, StaticDeviceInfo

if TYPE_CHECKING:
    from deebot_client.authentication import RestConfiguration


def _api_device(
    *,
    service_mqs: str | None = "api-ngiot.dc-na.ww.ecouser.net",
) -> ApiDeviceInfo:
    device: dict[str, Any] = {
        "did": "did-1",
        "class": "eyfj07",
        "company": "eco-ng",
        "name": "robot",
        "resource": "res-1",
    }
    if service_mqs is not None:
        device["service"] = {"mqs": service_mqs}
    return cast("ApiDeviceInfo", device)


def _ngiot_static_device_info() -> StaticDeviceInfo:
    return StaticDeviceInfo(
        data_type=DataType.JSON,
        capabilities=cast(
            "Any",
            {
                "battery": {
                    "get": [GetBattery()],
                },
            },
        ),
    )


def _non_ngiot_static_device_info() -> StaticDeviceInfo:
    return StaticDeviceInfo(
        data_type=DataType.JSON,
        capabilities=cast("Any", {}),
    )


def test_uses_ngiot_detects_ngiot_command(
    rest_config: RestConfiguration,
) -> None:
    authenticator = Authenticator(rest_config, "account", "password")

    assert authenticator._uses_ngiot(_ngiot_static_device_info()) is True


def test_uses_ngiot_returns_false_for_non_ngiot_profile(
    rest_config: RestConfiguration,
) -> None:
    authenticator = Authenticator(rest_config, "account", "password")

    assert authenticator._uses_ngiot(_non_ngiot_static_device_info()) is False


async def test_ensure_ngiot_for_device_attaches_ngiot_stack(
    rest_config: RestConfiguration,
) -> None:
    authenticator = Authenticator(rest_config, "account", "password")

    attached = await authenticator.ensure_ngiot_for_device(
        _api_device(),
        _ngiot_static_device_info(),
    )

    assert attached is True
    assert authenticator.sst_authenticator is not None
    assert authenticator.ngiot_client is not None
    assert authenticator._ngiot_base_url == "https://api-base.dc-na.ww.ecouser.net"


async def test_ensure_ngiot_for_device_does_not_attach_for_non_ngiot_profile(
    rest_config: RestConfiguration,
) -> None:
    authenticator = Authenticator(rest_config, "account", "password")

    attached = await authenticator.ensure_ngiot_for_device(
        _api_device(),
        _non_ngiot_static_device_info(),
    )

    assert attached is False
    assert authenticator.sst_authenticator is None
    assert authenticator.ngiot_client is None
    assert authenticator._ngiot_base_url is None


async def test_ensure_ngiot_for_device_is_idempotent_for_same_base_url(
    rest_config: RestConfiguration,
) -> None:
    authenticator = Authenticator(rest_config, "account", "password")

    assert await authenticator.ensure_ngiot_for_device(
        _api_device(),
        _ngiot_static_device_info(),
    )

    sst_authenticator = authenticator.sst_authenticator
    ngiot_client = authenticator.ngiot_client

    assert await authenticator.ensure_ngiot_for_device(
        _api_device(),
        _ngiot_static_device_info(),
    )

    assert authenticator.sst_authenticator is sst_authenticator
    assert authenticator.ngiot_client is ngiot_client


async def test_ensure_ngiot_for_device_reattaches_for_different_base_url(
    rest_config: RestConfiguration,
) -> None:
    authenticator = Authenticator(rest_config, "account", "password")

    assert await authenticator.ensure_ngiot_for_device(
        _api_device(service_mqs="api-ngiot.dc-na.ww.ecouser.net"),
        _ngiot_static_device_info(),
    )

    sst_authenticator = authenticator.sst_authenticator
    assert sst_authenticator is not None

    with patch.object(sst_authenticator, "teardown", AsyncMock()) as teardown:
        assert await authenticator.ensure_ngiot_for_device(
            _api_device(service_mqs="api-ngiot.dc-eu.ww.ecouser.net"),
            _ngiot_static_device_info(),
        )

    teardown.assert_awaited_once()
    assert authenticator.sst_authenticator is not None
    assert authenticator.sst_authenticator is not sst_authenticator
    assert authenticator.ngiot_client is not None
    assert authenticator._ngiot_base_url == "https://api-base.dc-eu.ww.ecouser.net"


async def test_ensure_ngiot_for_device_requires_mqs_or_configured_region(
    rest_config: RestConfiguration,
) -> None:
    authenticator = Authenticator(rest_config, "account", "password")

    with pytest.raises(ApiError, match="Could not resolve NGIOT base URL"):
        await authenticator.ensure_ngiot_for_device(
            _api_device(service_mqs=None),
            _ngiot_static_device_info(),
        )


async def test_ensure_ngiot_for_device_uses_configured_region(
    rest_config: RestConfiguration,
) -> None:
    authenticator = Authenticator(rest_config, "account", "password")
    authenticator.configure_ngiot(NgiotConfiguration(region="eu"))

    assert await authenticator.ensure_ngiot_for_device(
        _api_device(service_mqs=None),
        _ngiot_static_device_info(),
    )

    assert authenticator._ngiot_base_url == "https://api-base.dc-eu.ww.ecouser.net"


async def test_teardown_clears_ngiot_transport(
    rest_config: RestConfiguration,
) -> None:
    authenticator = Authenticator(rest_config, "account", "password")
    authenticator.attach_ngiot(NgiotConfiguration(region="na"))

    sst_authenticator = authenticator.sst_authenticator
    assert sst_authenticator is not None

    with patch.object(sst_authenticator, "teardown", AsyncMock()) as teardown:
        await authenticator.teardown()

    teardown.assert_awaited_once()
    assert authenticator.sst_authenticator is None
    assert authenticator.ngiot_client is None
    assert authenticator._ngiot_base_url is None
