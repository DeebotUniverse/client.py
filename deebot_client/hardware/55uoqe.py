"""DEEBOT MINI Capabilities."""

from __future__ import annotations

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
from deebot_client.commands import StationAction
from deebot_client.commands.json import station_action
from deebot_client.commands.json.auto_empty import GetAutoEmpty, SetAutoEmpty
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.border_spin import GetBorderSpin, SetBorderSpin
from deebot_client.commands.json.carpet import (
    GetCarpetAutoFanBoost,
    SetCarpetAutoFanBoost,
)
from deebot_client.commands.json.charge import Charge
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.child_lock import GetChildLock, SetChildLock
from deebot_client.commands.json.clean import (
    Clean,
    CleanArea,
    GetCleanInfo,
)
from deebot_client.commands.json.clean_count import GetCleanCount, SetCleanCount
from deebot_client.commands.json.clean_logs import GetCleanLogs
from deebot_client.commands.json.continuous_cleaning import (
    GetContinuousCleaning,
    SetContinuousCleaning,
)
from deebot_client.commands.json.custom import CustomCommand
from deebot_client.commands.json.efficiency import GetEfficiencyMode, SetEfficiencyMode
from deebot_client.commands.json.error import GetError
from deebot_client.commands.json.fan_speed import GetFanSpeed, SetFanSpeed
from deebot_client.commands.json.life_span import GetLifeSpan, ResetLifeSpan
from deebot_client.commands.json.map import (
    GetCachedMapInfo,
    GetMajorMap,
    GetMapInfoV2,
    GetMapSetV2,
    GetMapTrace,
    GetMinorMap,
)
from deebot_client.commands.json.map.major_map import SetMajorMap
from deebot_client.commands.json.mop_auto_wash_frequency import (
    GetMopAutoWashFrequency,
    SetMopAutoWashFrequency,
)
from deebot_client.commands.json.multimap_state import (
    GetMultimapState,
    SetMultimapState,
)
from deebot_client.commands.json.network import GetNetInfo
from deebot_client.commands.json.ota import GetOta, SetOta
from deebot_client.commands.json.play_sound import PlaySound
from deebot_client.commands.json.pos import GetPos
from deebot_client.commands.json.station_state import GetStationState
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.commands.json.sweep_mode import GetSweepMode, SetSweepMode
from deebot_client.commands.json.true_detect import GetTrueDetect, SetTrueDetect
from deebot_client.commands.json.volume import GetVolume, SetVolume
from deebot_client.commands.json.water_info import GetWaterInfo, SetWaterInfo
from deebot_client.commands.json.work_mode import GetWorkMode, SetWorkMode
from deebot_client.const import DataType
from deebot_client.events import (
    AvailabilityEvent,
    BatteryEvent,
    BorderSpinEvent,
    CachedMapInfoEvent,
    CarpetAutoFanBoostEvent,
    ChildLockEvent,
    CleanCountEvent,
    CleanLogEvent,
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
    OtaEvent,
    PositionsEvent,
    ReportStatsEvent,
    RoomsEvent,
    StateEvent,
    StatsEvent,
    SweepModeEvent,
    TotalStatsEvent,
    TrueDetectEvent,
    VolumeEvent,
    auto_empty,
    water_info,
)
from deebot_client.events.auto_empty import AutoEmptyEvent
from deebot_client.events.efficiency_mode import EfficiencyMode, EfficiencyModeEvent
from deebot_client.events.mop_auto_wash_frequency import MopAutoWashFrequencyEvent
from deebot_client.events.station import StationEvent
from deebot_client.events.work_mode import WorkMode, WorkModeEvent
from deebot_client.models import StaticDeviceInfo


def get_device_info() -> StaticDeviceInfo:
    """Get device info for this model."""
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
                log=CapabilityEvent(CleanLogEvent, [GetCleanLogs()]),
                work_mode=CapabilitySetTypes(
                    event=WorkModeEvent,
                    get=[GetWorkMode()],
                    set=SetWorkMode,
                    types=(
                        WorkMode.MOP,
                        WorkMode.VACUUM,
                        WorkMode.VACUUM_AND_MOP,
                    ),
                ),
            ),
            custom=CapabilityCustomCommand(
                event=CustomCommandEvent,
                get=[],
                set=CustomCommand,
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
                types=(
                    LifeSpan.BRUSH,
                    LifeSpan.FILTER,
                    LifeSpan.SIDE_BRUSH,
                    LifeSpan.UNIT_CARE,
                    LifeSpan.ROUND_MOP,
                    LifeSpan.DUST_BAG,
                ),
                event=LifeSpanEvent,
                get=[
                    GetLifeSpan(
                        [
                            LifeSpan.BRUSH,
                            LifeSpan.FILTER,
                            LifeSpan.SIDE_BRUSH,
                            LifeSpan.UNIT_CARE,
                            LifeSpan.ROUND_MOP,
                            LifeSpan.DUST_BAG,
                        ]
                    )
                ],
                reset=ResetLifeSpan,
            ),
            map=CapabilityMap(
                cached_info=CapabilityEvent(CachedMapInfoEvent, [GetCachedMapInfo()]),
                changed=CapabilityEvent(MapChangedEvent, []),
                info=CapabilityExecute(GetMapInfoV2),
                major=CapabilitySet(MajorMapEvent, [GetMajorMap()], SetMajorMap),
                minor=CapabilityExecute(GetMinorMap),
                multi_state=CapabilitySetEnable(
                    MultimapStateEvent, [GetMultimapState()], SetMultimapState
                ),
                position=CapabilityEvent(PositionsEvent, [GetPos()]),
                rooms=CapabilityEvent(RoomsEvent, [GetCachedMapInfo()]),
                set=CapabilityExecute(GetMapSetV2),
                trace=CapabilityEvent(MapTraceEvent, [GetMapTrace()]),
            ),
            network=CapabilityEvent(NetworkInfoEvent, [GetNetInfo()]),
            play_sound=CapabilityExecute(PlaySound),
            settings=CapabilitySettings(
                border_spin=CapabilitySetEnable(
                    BorderSpinEvent,
                    [GetBorderSpin()],
                    SetBorderSpin,
                ),
                carpet_auto_fan_boost=CapabilitySetEnable(
                    CarpetAutoFanBoostEvent,
                    [GetCarpetAutoFanBoost()],
                    SetCarpetAutoFanBoost,
                ),
                child_lock=CapabilitySetEnable(
                    ChildLockEvent,
                    [GetChildLock()],
                    SetChildLock,
                ),
                efficiency_mode=CapabilitySetTypes(
                    event=EfficiencyModeEvent,
                    get=[GetEfficiencyMode()],
                    set=SetEfficiencyMode,
                    types=(
                        EfficiencyMode.ENERGY_EFFICIENT_MODE,
                        EfficiencyMode.STANDARD_MODE,
                    ),
                ),
                mop_auto_wash_frequency=CapabilityNumber(
                    event=MopAutoWashFrequencyEvent,
                    get=[GetMopAutoWashFrequency()],
                    set=SetMopAutoWashFrequency,
                    min=0,
                    max=60,
                ),
                ota=CapabilitySetEnable(OtaEvent, [GetOta()], SetOta),
                sweep_mode=CapabilitySetEnable(
                    SweepModeEvent,
                    [GetSweepMode()],
                    SetSweepMode,
                ),
                true_detect=CapabilitySetEnable(
                    TrueDetectEvent,
                    [GetTrueDetect()],
                    SetTrueDetect,
                ),
                volume=CapabilitySet(VolumeEvent, [GetVolume()], SetVolume),
            ),
            state=CapabilityEvent(StateEvent, [GetChargeState(), GetCleanInfo()]),
            station=CapabilityStation(
                action=CapabilityExecuteTypes(
                    station_action.StationAction,
                    types=(
                        StationAction.EMPTY_DUSTBIN,
                        StationAction.DRY_MOP,
                        StationAction.CLEAN_BASE,
                    ),
                ),
                auto_empty=CapabilitySetTypes(
                    event=AutoEmptyEvent,
                    get=[GetAutoEmpty()],
                    set=SetAutoEmpty,
                    types=(
                        auto_empty.Frequency.AUTO,
                        auto_empty.Frequency.SMART,
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
