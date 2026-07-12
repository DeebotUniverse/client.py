"""Yeedi vacuum capabilities for hardware class 6r6dbt."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from deebot_client.capabilities import CapabilitySetTypes, CapabilityWater
from deebot_client.commands.json.water_info import SetWaterInfo
from deebot_client.events import water_info
from deebot_client.hardware import kd0una

if TYPE_CHECKING:
    from deebot_client.models import StaticDeviceInfo


def get_device_info() -> StaticDeviceInfo:
    """Get device info for this model.

    The 6r6dbt class is reported by a Yeedi cloud-MQTT vacuum. Start with the
    Yeedi Floor 3 Station capability profile, which uses the same JSON command
    family and includes the core vacuum commands needed by Home Assistant.
    """
    info = kd0una.get_device_info()
    capabilities = info.capabilities
    water_capability = capabilities.water
    if water_capability is None:
        return info

    return replace(
        info,
        capabilities=replace(
            capabilities,
            water=CapabilityWater(
                amount=CapabilitySetTypes(
                    event=water_info.WaterAmountEvent,
                    get=water_capability.amount.get,
                    set=SetWaterInfo,
                    types=(
                        water_info.WaterAmount.OFF,
                        water_info.WaterAmount.LOW,
                        water_info.WaterAmount.MEDIUM,
                        water_info.WaterAmount.HIGH,
                    ),
                ),
                mop_attached=water_capability.mop_attached,
            ),
        ),
    )
