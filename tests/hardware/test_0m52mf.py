"""Discovery and consumable requests for the GOAT A2000 LiDAR PRO."""

from __future__ import annotations

from dataclasses import fields
from unittest.mock import AsyncMock

from deebot_client.api_client import ApiClient
from deebot_client.capabilities import DeviceType
from deebot_client.const import DataType
from deebot_client.events import LifeSpan
from deebot_client.hardware import get_static_device_info


async def test_a2000_is_discovered_as_a_json_mower() -> None:
    authenticator = AsyncMock()
    authenticator.post_authenticated.return_value = {
        "devices": [
            {
                "did": "example-a2000",
                "class": "0m52mf",
                "company": "eco-ng",
                "deviceName": "GOAT A2000 LiDAR PRO",
            }
        ]
    }

    devices = await ApiClient(authenticator).get_devices()

    assert not devices.not_supported
    assert not devices.xmpp
    assert len(devices.mqtt) == 1
    assert devices.mqtt[0].api["class"] == "0m52mf"
    assert devices.mqtt[0].static.data_type is DataType.JSON
    assert devices.mqtt[0].static.capabilities.device_type is DeviceType.MOWER


async def test_a2000_does_not_inherit_unverified_settings_or_area_commands() -> None:
    info = await get_static_device_info("0m52mf")
    assert info is not None
    assert info.capabilities.clean.action.area is None
    assert all(
        getattr(info.capabilities.settings, field.name) is None
        for field in fields(info.capabilities.settings)
    )


async def test_a2000_requests_all_three_supported_consumables() -> None:
    info = await get_static_device_info("0m52mf")
    assert info is not None
    capability = info.capabilities.life_span
    assert capability is not None
    assert capability.types == (
        LifeSpan.BLADE,
        LifeSpan.TRIMMER_BRUSH,
        LifeSpan.WEED_ROPE,
    )
    assert capability.get[0]._get_payload()["body"]["data"] == [
        "blade",
        "trimmerBrush",
        "weedRope",
    ]
