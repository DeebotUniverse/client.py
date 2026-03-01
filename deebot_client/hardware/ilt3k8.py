"""DEEBOT X9 PRO OMNI Capabilities."""

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
from deebot_client.commands.json import (
    station_action,
)
from deebot_client.commands.json.advanced_mode import GetAdvancedMode, SetAdvancedMode
from deebot_client.commands.json.auto_empty import GetAutoEmpty, SetAutoEmpty
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.carpet import (
    GetCarpetAutoFanBoost,
    SetCarpetAutoFanBoost,
)
from deebot_client.commands.json.charge import Charge
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.child_lock import GetChildLock, SetChildLock
from deebot_client.commands.json.clean import (
    CleanArea,
    CleanV2,
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
    SetMajorMap,
)
from deebot_client.commands.json.mop_auto_wash_frequency import (
    GetMopAutoWashFrequency,
    SetMopAutoWashFrequency,
)
from deebot_client.commands.json.network import GetNetInfo
from deebot_client.commands.json.ota import GetOta, SetOta
from deebot_client.commands.json.play_sound import PlaySound
from deebot_client.commands.json.pos import GetPos
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.commands.json.sweep_mode import GetSweepMode, SetSweepMode
from deebot_client.commands.json.voice_assistant_state import (
    GetVoiceAssistantState,
    SetVoiceAssistantState,
)
from deebot_client.commands.json.volume import GetVolume, SetVolume
from deebot_client.commands.json.water_info import GetWaterInfo, SetWaterInfo
from deebot_client.commands.json.work_mode import GetWorkMode, SetWorkMode
from deebot_client.commands.json.work_state import GetWorkState
from deebot_client.const import DataType
from deebot_client.events import (
    AdvancedModeEvent,
    AvailabilityEvent,
    BatteryEvent,
    CarpetAutoFanBoostEvent,
    ChildLockEvent,
    CleanCountEvent,
    CleanLogEvent,
    ContinuousCleaningEvent,
    CustomCommandEvent,
    EfficiencyModeEvent,
    ErrorEvent,
    FanSpeedEvent,
    FanSpeedLevel,
    LifeSpan,
    LifeSpanEvent,
    MapChangedEvent,
    NetworkInfoEvent,
    OtaEvent,
    ReportStatsEvent,
    RoomsEvent,
    StateEvent,
    StationEvent,
    StatsEvent,
    SweepModeEvent,
    TotalStatsEvent,
    VoiceAssistantStateEvent,
    VolumeEvent,
    WorkMode,
    WorkModeEvent,
    auto_empty,
    water_info,
)
from deebot_client.events.auto_empty import AutoEmptyEvent
from deebot_client.events.efficiency_mode import EfficiencyMode
from deebot_client.events.map import (
    CachedMapInfoEvent,
    MajorMapEvent,
    MapTraceEvent,
    PositionsEvent,
)
from deebot_client.events.mop_auto_wash_frequency import MopAutoWashFrequencyEvent
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
                action=CapabilityCleanAction(command=CleanV2, area=CleanArea),
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
                        WorkMode.MOP_AFTER_VACUUM,
                        WorkMode.VACUUM,
                        WorkMode.VACUUM_AND_MOP,
                    ),
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
                types=(
                    LifeSpan.BRUSH,
                    LifeSpan.CLEANING_SOLUTION,
                    LifeSpan.DUST_BAG,
                    LifeSpan.HAND_FILTER,
                    LifeSpan.FILTER,  # heap
                    LifeSpan.ROUND_MOP,
                    LifeSpan.SEWAGE_BOX,
                    LifeSpan.SIDE_BRUSH,
                    LifeSpan.STRAINER,
                    LifeSpan.UNIT_CARE,
                    LifeSpan.WATER_SINK,
                ),
                event=LifeSpanEvent,
                get=[
                    GetLifeSpan(
                        [
                            LifeSpan.BRUSH,
                            LifeSpan.CLEANING_SOLUTION,
                            LifeSpan.DUST_BAG,
                            LifeSpan.HAND_FILTER,
                            LifeSpan.FILTER,  # heap
                            LifeSpan.ROUND_MOP,
                            LifeSpan.SEWAGE_BOX,
                            LifeSpan.SIDE_BRUSH,
                            LifeSpan.STRAINER,
                            LifeSpan.UNIT_CARE,
                            LifeSpan.WATER_SINK,
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
                position=CapabilityEvent(PositionsEvent, [GetPos()]),
                rooms=CapabilityEvent(RoomsEvent, [GetCachedMapInfo()]),
                set=CapabilityExecute(GetMapSetV2),
                trace=CapabilityEvent(MapTraceEvent, [GetMapTrace()]),
            ),
            network=CapabilityEvent(NetworkInfoEvent, [GetNetInfo()]),
            play_sound=CapabilityExecute(PlaySound),
            settings=CapabilitySettings(
                advanced_mode=CapabilitySetEnable(
                    AdvancedModeEvent, [GetAdvancedMode()], SetAdvancedMode
                ),
                carpet_auto_fan_boost=CapabilitySetEnable(
                    CarpetAutoFanBoostEvent,
                    [GetCarpetAutoFanBoost()],
                    SetCarpetAutoFanBoost,
                ),
                child_lock=CapabilitySetEnable(
                    ChildLockEvent, [GetChildLock()], SetChildLock
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
                    SweepModeEvent, [GetSweepMode()], SetSweepMode
                ),
                voice_assistant=CapabilitySetEnable(
                    VoiceAssistantStateEvent,
                    [GetVoiceAssistantState()],
                    SetVoiceAssistantState,
                ),
                volume=CapabilitySet(VolumeEvent, [GetVolume()], SetVolume),
                # TODO: add true detect once the implementation supports the 'level' attribute
            ),
            state=CapabilityEvent(StateEvent, [GetChargeState(), GetWorkState()]),
            station=CapabilityStation(
                action=CapabilityExecuteTypes(
                    station_action.StationAction, types=(StationAction.EMPTY_DUSTBIN,)
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
                state=CapabilityEvent(StationEvent, [GetWorkState()]),
            ),
            stats=CapabilityStats(
                clean=CapabilityEvent(StatsEvent, [GetStats()]),
                report=CapabilityEvent(ReportStatsEvent, []),
                total=CapabilityEvent(TotalStatsEvent, [GetTotalStats()]),
            ),
            water=CapabilityWater(
                amount=CapabilityNumber(
                    event=water_info.WaterCustomAmountEvent,
                    get=[GetWaterInfo()],
                    set=lambda custom_amount: SetWaterInfo(custom_amount=custom_amount),
                    min=0,
                    max=50,
                ),
                mop_attached=CapabilityEvent(
                    water_info.MopAttachedEvent, [GetWaterInfo()]
                ),
            ),
        ),
    )
