from __future__ import annotations

from deebot_client import hardware
from deebot_client.capabilities import (
    CapabilitySet,
    CapabilitySetEnable,
    CapabilitySetTypes,
)
from deebot_client.commands.json.native_area import native_clean_area
from deebot_client.commands.json.native_control import (
    NativeCustomCommand,
    NativeLocate,
    NativeResetLifeSpan,
    NativeReturnToDock,
    NativeSetFanSpeed,
    NativeSetWaterAmount,
    native_clean,
)
from deebot_client.commands.json.native_info import GetNativeInfo
from deebot_client.commands.json.native_map import GetNativeMapData, NativeMapSwitch
from deebot_client.commands.json.native_settings import (
    NativeSetAutoBoost,
    NativeSetChildLock,
    NativeSetContinuousCleaning,
    NativeSetDoNotDisturb,
    NativeSetVolume,
)
from deebot_client.const import DataType
from deebot_client.events import (
    AvailabilityEvent,
    BatteryEvent,
    CachedMapInfoEvent,
    CarpetAutoFanBoostEvent,
    ChildLockEvent,
    ContinuousCleaningEvent,
    CustomCommandEvent,
    DoNotDisturbEvent,
    ErrorEvent,
    FanSpeedEvent,
    FanSpeedLevel,
    LifeSpan,
    LifeSpanEvent,
    MapTraceEvent,
    NativeTraceEvent,
    NetworkInfoEvent,
    PositionsEvent,
    ReportStatsEvent,
    RoomsEvent,
    StateEvent,
    StatsEvent,
    TotalStatsEvent,
    VolumeEvent,
    water_info,
)
from deebot_client.hardware.cqyi87 import get_device_info
from deebot_client.models import CleanAction


async def test_cqyi87_discovered_through_loader() -> None:
    info = await hardware.get_static_device_info("cqyi87")
    assert info is not None
    assert info == get_device_info()
    assert info.data_type == DataType.JSON


def test_cqyi87_clean_charge_sound() -> None:
    capabilities = get_device_info().capabilities

    assert capabilities.clean.action.command is native_clean
    assert capabilities.clean.action.command(CleanAction.STOP).NAME == "40013"
    assert capabilities.clean.action.area is native_clean_area
    assert capabilities.clean.continuous is not None
    assert capabilities.clean.continuous.set is NativeSetContinuousCleaning
    assert capabilities.clean.continuous.get == [GetNativeInfo(["breakCleanSwitch"])]
    assert capabilities.charge.execute is NativeReturnToDock
    assert capabilities.play_sound.execute is NativeLocate
    assert capabilities.map is not None
    assert capabilities.map.map_switch is not None
    assert capabilities.map.map_switch.execute is NativeMapSwitch
    assert capabilities.map.edit is not None
    assert capabilities.station is None


def test_cqyi87_events_and_getters() -> None:
    capabilities = get_device_info().capabilities

    assert capabilities.get_refresh_commands(AvailabilityEvent) == [
        GetNativeInfo(["battery"], is_available_check=True)
    ]
    assert capabilities.get_refresh_commands(BatteryEvent) == [
        GetNativeInfo(["battery"])
    ]
    assert capabilities.get_refresh_commands(ErrorEvent) == [GetNativeInfo(["error"])]
    assert capabilities.get_refresh_commands(NetworkInfoEvent) == [
        GetNativeInfo(["deviceInfo"])
    ]
    assert capabilities.get_refresh_commands(LifeSpanEvent) == [
        GetNativeInfo(["consumables"])
    ]
    assert capabilities.get_refresh_commands(StatsEvent) == [
        GetNativeInfo(["cleanArea", "cleanTime"])
    ]
    assert capabilities.get_refresh_commands(ReportStatsEvent) == []
    assert capabilities.get_refresh_commands(TotalStatsEvent) == []
    assert capabilities.get_refresh_commands(StateEvent) == [GetNativeInfo()]
    assert capabilities.get_refresh_commands(CachedMapInfoEvent) == [
        GetNativeMapData.get_catalog()
    ]
    assert capabilities.get_refresh_commands(PositionsEvent) == [
        GetNativeMapData.get_catalog()
    ]
    assert capabilities.get_refresh_commands(RoomsEvent) == [
        GetNativeMapData.get_catalog()
    ]
    assert capabilities.get_refresh_commands(NativeTraceEvent) == [
        GetNativeMapData.get_catalog()
    ]
    assert capabilities.get_refresh_commands(MapTraceEvent) == []
    assert capabilities.get_refresh_commands(FanSpeedEvent) == [
        GetNativeInfo(["fanMode"])
    ]
    assert capabilities.get_refresh_commands(water_info.WaterAmountEvent) == [
        GetNativeInfo(["waterMode"])
    ]
    assert capabilities.get_refresh_commands(water_info.MopAttachedEvent) == [
        GetNativeInfo(["mopState"])
    ]
    assert capabilities.get_refresh_commands(ChildLockEvent) == [
        GetNativeInfo(["childLock"])
    ]
    assert capabilities.get_refresh_commands(CarpetAutoFanBoostEvent) == [
        GetNativeInfo(["autoBoost"])
    ]
    assert capabilities.get_refresh_commands(ContinuousCleaningEvent) == [
        GetNativeInfo(["breakCleanSwitch"])
    ]
    assert capabilities.get_refresh_commands(DoNotDisturbEvent) == [
        GetNativeInfo(["disturbSwitch"])
    ]
    assert capabilities.get_refresh_commands(VolumeEvent) == [GetNativeInfo(["volume"])]
    assert capabilities.get_refresh_commands(CustomCommandEvent) == []


def test_cqyi87_set_types() -> None:
    capabilities = get_device_info().capabilities

    assert capabilities.fan_speed is not None
    assert capabilities.fan_speed.set is NativeSetFanSpeed
    assert capabilities.fan_speed.types == (
        FanSpeedLevel.QUIET,
        FanSpeedLevel.NORMAL,
        FanSpeedLevel.MAX,
        FanSpeedLevel.MAX_PLUS,
    )

    assert capabilities.water is not None
    amount = capabilities.water.amount
    assert isinstance(amount, CapabilitySetTypes)
    assert amount.set is NativeSetWaterAmount
    assert amount.types == (
        water_info.WaterAmount.LOW,
        water_info.WaterAmount.MEDIUM,
        water_info.WaterAmount.HIGH,
    )

    assert capabilities.life_span.types == (
        LifeSpan.BRUSH,
        LifeSpan.FILTER,
        LifeSpan.SIDE_BRUSH,
        LifeSpan.UNIT_CARE,
    )
    assert capabilities.life_span.reset is NativeResetLifeSpan
    assert capabilities.custom.set is NativeCustomCommand

    settings = capabilities.settings
    assert isinstance(settings.child_lock, CapabilitySetEnable)
    assert settings.child_lock.set is NativeSetChildLock
    assert settings.child_lock.get == [GetNativeInfo(["childLock"])]

    assert isinstance(settings.carpet_auto_fan_boost, CapabilitySetEnable)
    assert settings.carpet_auto_fan_boost.set is NativeSetAutoBoost
    assert settings.carpet_auto_fan_boost.get == [GetNativeInfo(["autoBoost"])]

    assert isinstance(settings.do_not_disturb, CapabilitySetEnable)
    assert settings.do_not_disturb.set is NativeSetDoNotDisturb
    assert settings.do_not_disturb.get == [GetNativeInfo(["disturbSwitch"])]

    assert isinstance(settings.volume, CapabilitySet)
    assert settings.volume.set is NativeSetVolume
    assert settings.volume.get == [GetNativeInfo(["volume"])]
