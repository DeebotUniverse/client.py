"""Deebot N20 Pro Plus Capabilities."""

from __future__ import annotations

from deebot_client.capabilities import (
    Capabilities,
    CapabilityBaseStation,
    CapabilityClean,
    CapabilityCleanAction,
    CapabilityCustomCommand,
    CapabilityEvent,
    CapabilityExecute,
    CapabilityExecuteTypes,
    CapabilityLifeSpan,
    CapabilityMap,
    CapabilitySet,
    CapabilitySetEnable,
    CapabilitySettings,
    CapabilitySetTypes,
    CapabilityStats,
    DeviceType,
)
from deebot_client.commands import BaseStationAction
from deebot_client.commands.json.auto_empty import GetAutoEmpty, SetAutoEmpty
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.carpet import (
    GetCarpetAutoFanBoost,
    SetCarpetAutoFanBoost,
)
from deebot_client.commands.json.charge import Charge
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.child_lock import GetChildLock, SetChildLock
from deebot_client.commands.json.clean import CleanAreaV2, CleanV2, GetCleanInfoV2
from deebot_client.commands.json.clean_count import GetCleanCount, SetCleanCount
from deebot_client.commands.json.clean_logs import GetCleanLogs
from deebot_client.commands.json.continuous_cleaning import (
    GetContinuousCleaning,
    SetContinuousCleaning,
)
from deebot_client.commands.json.custom import CustomCommand
from deebot_client.commands.json.error import GetError
from deebot_client.commands.json.fan_speed import GetFanSpeed, SetFanSpeed
from deebot_client.commands.json.life_span import GetLifeSpan, ResetLifeSpan
from deebot_client.commands.json.map import GetCachedMapInfo, GetMajorMap, GetMapTrace
from deebot_client.commands.json.multimap_state import (
    GetMultimapState,
    SetMultimapState,
)
from deebot_client.commands.json.network import GetNetInfo
from deebot_client.commands.json.play_sound import PlaySound
from deebot_client.commands.json.pos import GetPos
from deebot_client.commands.json.relocation import SetRelocationState
from deebot_client.commands.json.station_action import StationAction
from deebot_client.commands.json.station_state import GetStationState
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.commands.json.volume import GetVolume, SetVolume
from deebot_client.commands.json.water_info import GetWaterInfo, SetWaterInfo
from deebot_client.const import DataType
from deebot_client.events import (
    AutoEmptyEvent,
    AvailabilityEvent,
    BaseStationEvent,
    BatteryEvent,
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
    PositionsEvent,
    ReportStatsEvent,
    RoomsEvent,
    StateEvent,
    StatsEvent,
    TotalStatsEvent,
    VolumeEvent,
    WaterAmount,
    WaterInfoEvent,
    auto_empty,
)
from deebot_client.models import StaticDeviceInfo
from deebot_client.util import short_name

from . import DEVICES

DEVICES[short_name(__name__)] = StaticDeviceInfo(
    DataType.JSON,
    Capabilities(
        device_type=DeviceType.VACUUM,
        availability=CapabilityEvent(
            AvailabilityEvent, [GetBattery(is_available_check=True)]
        ),
        battery=CapabilityEvent(BatteryEvent, [GetBattery()]),
        base_station=CapabilityBaseStation(
            action=CapabilityExecuteTypes(
                StationAction, types=(BaseStationAction.EMPTY_DUSTBIN,)
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
            status=CapabilityEvent(BaseStationEvent, [GetStationState()]),
        ),
        charge=CapabilityExecute(Charge),
        clean=CapabilityClean(
            action=CapabilityCleanAction(command=CleanV2, area=CleanAreaV2),
            continuous=CapabilitySetEnable(
                ContinuousCleaningEvent,
                [GetContinuousCleaning()],
                SetContinuousCleaning,
            ),
            count=CapabilitySet(CleanCountEvent, [GetCleanCount()], SetCleanCount),
            log=CapabilityEvent(CleanLogEvent, [GetCleanLogs()]),
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
                LifeSpan.FILTER,
                LifeSpan.SIDE_BRUSH,
                LifeSpan.UNIT_CARE,
                LifeSpan.ROUND_MOP,
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
                    ]
                )
            ],
            reset=ResetLifeSpan,
        ),
        map=CapabilityMap(
            cached_info=CapabilityEvent(
                CachedMapInfoEvent, [GetCachedMapInfo(version=2)]
            ),
            changed=CapabilityEvent(MapChangedEvent, []),
            major=CapabilityEvent(MajorMapEvent, [GetMajorMap()]),
            multi_state=CapabilitySetEnable(
                MultimapStateEvent, [GetMultimapState()], SetMultimapState
            ),
            position=CapabilityEvent(PositionsEvent, [GetPos()]),
            relocation=CapabilityExecute(SetRelocationState),
            rooms=CapabilityEvent(RoomsEvent, [GetCachedMapInfo(version=2)]),
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
            volume=CapabilitySet(VolumeEvent, [GetVolume()], SetVolume),
        ),
        state=CapabilityEvent(StateEvent, [GetChargeState(), GetCleanInfoV2()]),
        stats=CapabilityStats(
            clean=CapabilityEvent(StatsEvent, [GetStats()]),
            report=CapabilityEvent(ReportStatsEvent, []),
            total=CapabilityEvent(TotalStatsEvent, [GetTotalStats()]),
        ),
        water=CapabilitySetTypes(
            event=WaterInfoEvent,
            get=[GetWaterInfo()],
            set=SetWaterInfo,
            types=(
                WaterAmount.LOW,
                WaterAmount.MEDIUM,
                WaterAmount.HIGH,
            ),
        ),
    ),
)
