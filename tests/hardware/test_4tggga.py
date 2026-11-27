from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, cast

from deebot_client.capabilities import CapabilitySet
from deebot_client.commands import StationAction
from deebot_client.commands.json.auto_empty import GetAutoEmpty, SetAutoEmptyIntensity
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.clean import CleanV2, FreeCleanV2
from deebot_client.commands.json.custom_area_mode import (
    GetCustomAreaMode,
    SetCustomAreaMode,
)
from deebot_client.commands.json.drying_duration import (
    GetDryingDuration,
    SetDryingDuration,
)
from deebot_client.commands.json.map import (
    GetMapInfoV2,
    GetMapSetV2,
    GetMinorMap,
    SetMajorMap,
)
from deebot_client.commands.json.mop_auto_wash_frequency import (
    SetMopAutoWashFrequencyWithWiseMode,
)
from deebot_client.commands.json.true_detect import (
    GetTrueDetect,
    SetTrueDetectWithLevel,
)
from deebot_client.commands.json.work_state import GetWorkState
from deebot_client.const import DataType
from deebot_client.events import (
    AutoEmptyIntensity,
    CustomAreaMode,
    DryingDuration,
    auto_empty,
)

if TYPE_CHECKING:
    from deebot_client.models import StaticDeviceInfo


def _static_info() -> StaticDeviceInfo:
    module = importlib.import_module("deebot_client.hardware.4tggga")
    return cast("StaticDeviceInfo", module.get_device_info())


def test_4tggga_uses_v2_capabilities() -> None:
    static_info = _static_info()
    capabilities = static_info.capabilities

    assert static_info.data_type is DataType.JSON
    assert capabilities.clean.action.command is CleanV2
    assert capabilities.clean.action.area is FreeCleanV2
    assert capabilities.state.get == [GetChargeState(), GetWorkState()]

    assert capabilities.map is not None
    assert capabilities.map.info is not None
    assert capabilities.map.info.execute is GetMapInfoV2
    assert capabilities.map.set is not None
    assert capabilities.map.set.execute is GetMapSetV2
    assert capabilities.map.minor is not None
    assert capabilities.map.minor.execute is GetMinorMap
    assert capabilities.map.major is not None
    assert isinstance(capabilities.map.major, CapabilitySet)
    assert capabilities.map.major.set is SetMajorMap

    assert capabilities.station is not None
    assert capabilities.station.state.get == [GetWorkState()]
    assert capabilities.station.action.types == (
        StationAction.EMPTY_DUSTBIN,
        StationAction.WASH_MOP,
        StationAction.DRY_MOP,
    )


def test_4tggga_device_specific_settings() -> None:
    capabilities = _static_info().capabilities

    assert capabilities.settings.custom_area_mode is not None
    assert capabilities.settings.custom_area_mode.get == [GetCustomAreaMode()]
    assert capabilities.settings.custom_area_mode.set is SetCustomAreaMode
    assert capabilities.settings.custom_area_mode.types == (
        CustomAreaMode.STANDARD,
        CustomAreaMode.DEEP,
        CustomAreaMode.QUICK,
    )
    assert capabilities.settings.mop_auto_wash_frequency is not None
    assert capabilities.settings.mop_auto_wash_frequency.min == 6
    assert capabilities.settings.mop_auto_wash_frequency.max == 12
    assert (
        capabilities.settings.mop_auto_wash_frequency.set
        is SetMopAutoWashFrequencyWithWiseMode
    )
    assert capabilities.settings.true_detect is not None
    assert capabilities.settings.true_detect.get == [GetTrueDetect()]
    assert capabilities.settings.true_detect.set is SetTrueDetectWithLevel

    assert capabilities.station is not None
    assert capabilities.station.auto_empty.get == [GetAutoEmpty()]
    assert capabilities.station.auto_empty.types == (
        auto_empty.Frequency.AUTO,
        auto_empty.Frequency.SMART,
    )
    assert capabilities.station.auto_empty_intensity is not None
    assert capabilities.station.auto_empty_intensity.get == [GetAutoEmpty()]
    assert capabilities.station.auto_empty_intensity.set is SetAutoEmptyIntensity
    assert capabilities.station.auto_empty_intensity.types == (
        AutoEmptyIntensity.STANDARD,
        AutoEmptyIntensity.HIGH_FREQUENCY,
    )
    assert capabilities.station.drying_duration is not None
    assert capabilities.station.drying_duration.get == [GetDryingDuration()]
    assert capabilities.station.drying_duration.set is SetDryingDuration
    assert capabilities.station.drying_duration.types == (
        DryingDuration.TWO_HOURS,
        DryingDuration.THREE_HOURS,
        DryingDuration.FOUR_HOURS,
    )
