from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, patch

import pytest

from deebot_client.api_client import ApiClient
from deebot_client.authentication import Authenticator
from deebot_client.const import DataType
from deebot_client.models import ApiDeviceInfo, StaticDeviceInfo


def _api_device(
    *,
    class_id: str = "eyfj07",
    company: str = "eco-ng",
) -> ApiDeviceInfo:
    return cast(
        "ApiDeviceInfo",
        {
            "did": f"{class_id}-did",
            "class": class_id,
            "company": company,
            "name": "robot",
            "resource": "res-1",
            "service": {"mqs": "api-ngiot.dc-na.ww.ecouser.net"},
        },
    )


def _static_device_info() -> StaticDeviceInfo:
    return StaticDeviceInfo(
        data_type=DataType.JSON,
        capabilities=cast("Any", {}),
    )


@pytest.fixture
def authenticator() -> AsyncMock:
    auth = AsyncMock(spec_set=Authenticator)
    auth.ensure_ngiot_for_device.return_value = True
    return auth


async def test_get_devices_bootstraps_ngiot_for_supported_eco_ng_device(
    authenticator: AsyncMock,
) -> None:
    device = _api_device()
    static_device_info = _static_device_info()

    client = ApiClient(cast("Authenticator", authenticator))

    with (
        patch.object(
            client,
            "_get_devices",
            AsyncMock(
                side_effect=[
                    {device["did"]: device},
                    {},
                ]
            ),
        ),
        patch(
            "deebot_client.api_client.get_static_device_info",
            AsyncMock(return_value=static_device_info),
        ),
    ):
        devices = await client.get_devices()

    assert len(devices.mqtt) == 1
    assert devices.mqtt[0].api == device
    assert devices.mqtt[0].static == static_device_info
    authenticator.ensure_ngiot_for_device.assert_awaited_once_with(
        device,
        static_device_info,
    )


async def test_get_devices_does_not_bootstrap_ngiot_for_legacy_device(
    authenticator: AsyncMock,
) -> None:
    device = _api_device(class_id="legacy", company="eco-legacy")

    client = ApiClient(cast("Authenticator", authenticator))

    with patch.object(
        client,
        "_get_devices",
        AsyncMock(
            side_effect=[
                {device["did"]: device},
                {},
            ]
        ),
    ):
        devices = await client.get_devices()

    assert devices.mqtt == []
    assert devices.xmpp == [device]
    authenticator.ensure_ngiot_for_device.assert_not_awaited()


async def test_get_devices_does_not_bootstrap_unknown_eco_ng_device(
    authenticator: AsyncMock,
) -> None:
    device = _api_device(class_id="unknown")

    client = ApiClient(cast("Authenticator", authenticator))

    with (
        patch.object(
            client,
            "_get_devices",
            AsyncMock(
                side_effect=[
                    {device["did"]: device},
                    {},
                ]
            ),
        ),
        patch(
            "deebot_client.api_client.get_static_device_info",
            AsyncMock(return_value=None),
        ),
    ):
        devices = await client.get_devices()

    assert devices.mqtt == []
    assert devices.not_supported == [device]
    authenticator.ensure_ngiot_for_device.assert_not_awaited()


async def test_get_devices_propagates_ngiot_bootstrap_failure(
    authenticator: AsyncMock,
) -> None:
    device = _api_device()
    static_device_info = _static_device_info()
    authenticator.ensure_ngiot_for_device.side_effect = RuntimeError("boom")

    client = ApiClient(cast("Authenticator", authenticator))

    with (
        patch.object(
            client,
            "_get_devices",
            AsyncMock(
                side_effect=[
                    {device["did"]: device},
                    {},
                ]
            ),
        ),
        patch(
            "deebot_client.api_client.get_static_device_info",
            AsyncMock(return_value=static_device_info),
        ),
        pytest.raises(RuntimeError, match="boom"),
    ):
        await client.get_devices()
