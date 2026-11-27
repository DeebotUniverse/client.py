"""DEEBOT Y1 Pro Capabilities (cqyi87).

Control semantics: Stop ends the task and returns to dock (40013).
Pause halts in place (40009). No station or duration totals.
"""

from __future__ import annotations

from deebot_client.capabilities import (
    Capabilities,
    CapabilityClean,
    CapabilityCleanAction,
    CapabilityCustomCommand,
    CapabilityEvent,
    CapabilityExecute,
    CapabilityLifeSpan,
    CapabilityMap,
    CapabilitySet,
    CapabilitySetEnable,
    CapabilitySettings,
    CapabilitySetTypes,
    CapabilityStats,
    CapabilityWater,
    DeviceType,
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
from deebot_client.commands.json.native_map_edit import create_native_map_edit
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
    MapChangedEvent,
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
from deebot_client.models import StaticDeviceInfo


def _get_native_overlays(map_id: str, _set_type: object) -> GetNativeMapData:
    return GetNativeMapData.get_overlays(map_id)


def get_device_info() -> StaticDeviceInfo:
    """Get device info for this model."""
    life_span_types = (
        LifeSpan.BRUSH,
        LifeSpan.FILTER,
        LifeSpan.SIDE_BRUSH,
        LifeSpan.UNIT_CARE,
    )

    return StaticDeviceInfo(
        DataType.JSON,
        Capabilities(
            device_type=DeviceType.VACUUM,
            availability=CapabilityEvent(
                AvailabilityEvent, [GetNativeInfo(["battery"], is_available_check=True)]
            ),
            battery=CapabilityEvent(BatteryEvent, [GetNativeInfo(["battery"])]),
            charge=CapabilityExecute(NativeReturnToDock),
            clean=CapabilityClean(
                action=CapabilityCleanAction(
                    command=native_clean,
                    area=native_clean_area,
                ),
                continuous=CapabilitySetEnable(
                    ContinuousCleaningEvent,
                    [GetNativeInfo(["breakCleanSwitch"])],
                    NativeSetContinuousCleaning,
                ),
            ),
            custom=CapabilityCustomCommand(
                event=CustomCommandEvent, get=[], set=NativeCustomCommand
            ),
            error=CapabilityEvent(ErrorEvent, [GetNativeInfo(["error"])]),
            fan_speed=CapabilitySetTypes(
                event=FanSpeedEvent,
                get=[GetNativeInfo(["fanMode"])],
                set=NativeSetFanSpeed,
                types=(
                    FanSpeedLevel.QUIET,
                    FanSpeedLevel.NORMAL,
                    FanSpeedLevel.MAX,
                    FanSpeedLevel.MAX_PLUS,
                ),
            ),
            life_span=CapabilityLifeSpan(
                types=life_span_types,
                event=LifeSpanEvent,
                get=[GetNativeInfo(["consumables"])],
                reset=NativeResetLifeSpan,
            ),
            map=CapabilityMap(
                cached_info=CapabilityEvent(
                    CachedMapInfoEvent, [GetNativeMapData.get_catalog()]
                ),
                changed=CapabilityEvent(MapChangedEvent, []),
                position=CapabilityEvent(
                    PositionsEvent, [GetNativeMapData.get_catalog()]
                ),
                rooms=CapabilityEvent(RoomsEvent, [GetNativeMapData.get_catalog()]),
                trace=CapabilityEvent(
                    NativeTraceEvent, [GetNativeMapData.get_catalog()]
                ),
                info=CapabilityExecute(GetNativeMapData.get_map),
                map_switch=CapabilityExecute(NativeMapSwitch),
                set=CapabilityExecute(_get_native_overlays),
                edit=create_native_map_edit(),
            ),
            network=CapabilityEvent(NetworkInfoEvent, [GetNativeInfo(["deviceInfo"])]),
            play_sound=CapabilityExecute(NativeLocate),
            settings=CapabilitySettings(
                carpet_auto_fan_boost=CapabilitySetEnable(
                    CarpetAutoFanBoostEvent,
                    [GetNativeInfo(["autoBoost"])],
                    NativeSetAutoBoost,
                ),
                child_lock=CapabilitySetEnable(
                    ChildLockEvent,
                    [GetNativeInfo(["childLock"])],
                    NativeSetChildLock,
                ),
                do_not_disturb=CapabilitySetEnable(
                    DoNotDisturbEvent,
                    [GetNativeInfo(["disturbSwitch"])],
                    NativeSetDoNotDisturb,
                ),
                volume=CapabilitySet(
                    VolumeEvent,
                    [GetNativeInfo(["volume"])],
                    NativeSetVolume,
                ),
            ),
            state=CapabilityEvent(StateEvent, [GetNativeInfo()]),
            stats=CapabilityStats(
                clean=CapabilityEvent(
                    StatsEvent, [GetNativeInfo(["cleanArea", "cleanTime"])]
                ),
                report=CapabilityEvent(ReportStatsEvent, []),
                total=CapabilityEvent(TotalStatsEvent, []),
            ),
            water=CapabilityWater(
                amount=CapabilitySetTypes(
                    event=water_info.WaterAmountEvent,
                    get=[GetNativeInfo(["waterMode"])],
                    set=NativeSetWaterAmount,
                    types=(
                        water_info.WaterAmount.LOW,
                        water_info.WaterAmount.MEDIUM,
                        water_info.WaterAmount.HIGH,
                    ),
                ),
                mop_attached=CapabilityEvent(
                    water_info.MopAttachedEvent, [GetNativeInfo(["mopState"])]
                ),
            ),
        ),
    )
