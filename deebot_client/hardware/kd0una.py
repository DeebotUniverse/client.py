"""Yeedi Floor 3 Station Capabilities."""

from __future__ import annotations

from deebot_client import commands
from deebot_client.capabilities import (
    Capabilities,
    CapabilityClean,
    CapabilityCleanAction,
    CapabilityCustomCommand,
    CapabilityEvent,
    CapabilityExecute,
    CapabilityExecuteTypes,
    CapabilityLifeSpan,
    CapabilityMap,
    CapabilityNumber,
    CapabilitySet,
    CapabilitySetEnable,
    CapabilitySettings,
    CapabilitySetTypes,
    CapabilityStation,
    CapabilityStats,
    CapabilityWater,
    DeviceType,
)
from deebot_client.commands.json import station_action
from deebot_client.commands.json.auto_empty import GetAutoEmpty, SetAutoEmpty
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.carpet import (
    GetCarpetAutoFanBoost,
    SetCarpetAutoFanBoost,
)
from deebot_client.commands.json.charge import Charge
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.child_lock import GetChildLock, SetChildLock
from deebot_client.commands.json.clean import Clean, CleanArea, GetCleanInfo
from deebot_client.commands.json.clean_count import GetCleanCount, SetCleanCount
from deebot_client.commands.json.clean_preference import (
    GetCleanPreference,
    SetCleanPreference,
)
from deebot_client.commands.json.continuous_cleaning import (
    GetContinuousCleaning,
    SetContinuousCleaning,
)
from deebot_client.commands.json.custom import CustomCommand
from deebot_client.commands.json.error import GetError
from deebot_client.commands.json.fan_speed import GetFanSpeed, SetFanSpeed
from deebot_client.commands.json.life_span import GetLifeSpan, ResetLifeSpan
from deebot_client.commands.json.map import (
    GetCachedMapInfo,
    GetMajorMap,
    GetMapSet,
    GetMapTrace,
    GetMinorMap,
    SetMajorMap,
)
from deebot_client.commands.json.mop_auto_wash_frequency import (
    GetMopAutoWashFrequency,
    SetMopAutoWashFrequency,
)
from deebot_client.commands.json.multimap_state import (
    GetMultimapState,
    SetMultimapState,
)
from deebot_client.commands.json.network import GetNetInfo
from deebot_client.commands.json.play_sound import PlaySound
from deebot_client.commands.json.pos import GetPos
from deebot_client.commands.json.relocation import SetRelocationState
from deebot_client.commands.json.station_state import GetStationState
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.commands.json.true_detect import GetTrueDetect, SetTrueDetect
from deebot_client.commands.json.volume import GetVolume, SetVolume
from deebot_client.commands.json.water_info import GetWaterInfo, SetWaterInfo
from deebot_client.const import DataType
from deebot_client.events import (
    AutoEmptyEvent,
    AvailabilityEvent,
    BatteryEvent,
    CachedMapInfoEvent,
    CarpetAutoFanBoostEvent,
    ChildLockEvent,
    CleanCountEvent,
    CleanPreferenceEvent,
    ContinuousCleaningEvent,
    CustomCommandEvent,
    ErrorEvent,
    FanSpeedEvent,
    FanSpeedLevel,
    LifeSpan,
    LifeSpanEvent,
    MajorMapEvent,
    MapChangedEvent,
    MapTraceEvent,
    MultimapStateEvent,
    NetworkInfoEvent,
    PositionsEvent,
    ReportStatsEvent,
    RoomsEvent,
    StateEvent,
    StationEvent,
    StatsEvent,
    TotalStatsEvent,
    TrueDetectEvent,
    VolumeEvent,
    auto_empty,
    water_info,
)
from deebot_client.events.mop_auto_wash_frequency import MopAutoWashFrequencyEvent
from deebot_client.models import StaticDeviceInfo


def get_device_info() -> StaticDeviceInfo:
    """Get device info for Yeedi Floor 3 Station (kd0una)."""
    return StaticDeviceInfo(
        DataType.JSON,
        Capabilities(
            device_type=DeviceType.VACUUM,
            availability=CapabilityEvent(
                AvailabilityEvent, [GetBattery(is_available_check=True)]
            ),
            battery=CapabilityEvent(BatteryEvent, [GetBattery()]),
            charge=CapabilityExecute(Charge),
            clean=CapabilityClean(
                action=CapabilityCleanAction(command=Clean, area=CleanArea),
                continuous=CapabilitySetEnable(
                    ContinuousCleaningEvent,
                    [GetContinuousCleaning()],
                    SetContinuousCleaning,
                ),
                count=CapabilitySet(CleanCountEvent, [GetCleanCount()], SetCleanCount),
                preference=CapabilitySetEnable(
                    CleanPreferenceEvent, [GetCleanPreference()], SetCleanPreference
                ),
            ),
            custom=CapabilityCustomCommand(
                event=CustomCommandEvent, get=[], set=CustomCommand
            ),
            error=CapabilityEvent(ErrorEvent, [GetError()]),
            fan_speed=CapabilitySetTypes(
                event=FanSpeedEvent,
                get=[GetFanSpeed()],
                set=SetFanSpeed,
                types=(
                    FanSpeedLevel.QUIET,
                    FanSpeedLevel.NORMAL,
                    FanSpeedLevel.MAX,
                    FanSpeedLevel.MAX_PLUS,
                ),
            ),
            life_span=CapabilityLifeSpan(
                types=(LifeSpan.BRUSH, LifeSpan.FILTER, LifeSpan.SIDE_BRUSH),
                event=LifeSpanEvent,
                get=[
                    GetLifeSpan([LifeSpan.BRUSH, LifeSpan.FILTER, LifeSpan.SIDE_BRUSH])
                ],
                reset=ResetLifeSpan,
            ),
            map=CapabilityMap(
                cached_info=CapabilityEvent(CachedMapInfoEvent, [GetCachedMapInfo()]),
                changed=CapabilityEvent(MapChangedEvent, []),
                major=CapabilitySet(MajorMapEvent, [GetMajorMap()], SetMajorMap),
                minor=CapabilityExecute(GetMinorMap),
                multi_state=CapabilitySetEnable(
                    MultimapStateEvent, [GetMultimapState()], SetMultimapState
                ),
                position=CapabilityEvent(PositionsEvent, [GetPos()]),
                relocation=CapabilityExecute(SetRelocationState),
                rooms=CapabilityEvent(RoomsEvent, [GetCachedMapInfo()]),
                set=CapabilityExecute(GetMapSet),
                trace=CapabilityEvent(MapTraceEvent, [GetMapTrace()]),
            ),
            network=CapabilityEvent(NetworkInfoEvent, [GetNetInfo()]),
            play_sound=CapabilityExecute(PlaySound),
            settings=CapabilitySettings(
                carpet_auto_fan_boost=CapabilitySetEnable(
                    CarpetAutoFanBoostEvent,
                    [GetCarpetAutoFanBoost()],
                    SetCarpetAutoFanBoost,
                ),
                child_lock=CapabilitySetEnable(
                    ChildLockEvent, [GetChildLock()], SetChildLock
                ),
                mop_auto_wash_frequency=CapabilityNumber(
                    event=MopAutoWashFrequencyEvent,
                    get=[GetMopAutoWashFrequency()],
                    set=SetMopAutoWashFrequency,
                    min=0,
                    max=60,
                ),
                true_detect=CapabilitySetEnable(
                    TrueDetectEvent, [GetTrueDetect()], SetTrueDetect
                ),
                volume=CapabilitySet(VolumeEvent, [GetVolume()], SetVolume),
            ),
            state=CapabilityEvent(StateEvent, [GetChargeState(), GetCleanInfo()]),
            station=CapabilityStation(
                action=CapabilityExecuteTypes(
                    station_action.StationAction,
                    types=(
                        commands.StationAction.EMPTY_DUSTBIN,
                        commands.StationAction.DRY_MOP,
                        commands.StationAction.CLEAN_BASE,
                        commands.StationAction.WASH_MOP,
                    ),
                ),
                auto_empty=CapabilitySetTypes(
                    event=AutoEmptyEvent,
                    get=[GetAutoEmpty()],
                    set=SetAutoEmpty,
                    types=(
                        auto_empty.Frequency.AUTO,
                        auto_empty.Frequency.SMART,
                        auto_empty.Frequency.MIN_10,
                        auto_empty.Frequency.MIN_15,
                        auto_empty.Frequency.MIN_25,
                    ),
                ),
                state=CapabilityEvent(StationEvent, [GetStationState()]),
            ),
            stats=CapabilityStats(
                clean=CapabilityEvent(StatsEvent, [GetStats()]),
                report=CapabilityEvent(ReportStatsEvent, []),
                total=CapabilityEvent(TotalStatsEvent, [GetTotalStats()]),
            ),
            water=CapabilityWater(
                amount=CapabilitySetTypes(
                    event=water_info.WaterAmountEvent,
                    get=[GetWaterInfo()],
                    set=SetWaterInfo,
                    types=(
                        water_info.WaterAmount.LOW,
                        water_info.WaterAmount.MEDIUM,
                        water_info.WaterAmount.HIGH,
                        water_info.WaterAmount.ULTRAHIGH,
                    ),
                ),
                mop_attached=CapabilityEvent(
                    water_info.MopAttachedEvent, [GetWaterInfo()]
                ),
            ),
        ),
    )
