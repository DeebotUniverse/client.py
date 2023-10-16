"""Deebot ozmo 950 Capabilities."""
from deebot_client.capabilities import (
    Capabilities,
    CapabilityClean,
    CapabilityCleanAction,
    CapabilityEvent,
    CapabilityExecute,
    CapabilityLifeSpan,
    CapabilityMap,
    CapabilitySet,
    CapabilitySetEnable,
    CapabilitySettings,
    CapabilityStats,
)
from deebot_client.commands.json.advanced_mode import GetAdvancedMode, SetAdvancedMode
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.carpet import (
    GetCarpetAutoFanBoost,
    SetCarpetAutoFanBoost,
)
from deebot_client.commands.json.charge import Charge
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.clean import Clean, CleanArea, GetCleanInfo
from deebot_client.commands.json.clean_count import GetCleanCount, SetCleanCount
from deebot_client.commands.json.clean_logs import GetCleanLogs
from deebot_client.commands.json.clean_preference import (
    GetCleanPreference,
    SetCleanPreference,
)
from deebot_client.commands.json.continuous_cleaning import (
    GetContinuousCleaning,
    SetContinuousCleaning,
)
from deebot_client.commands.json.error import GetError
from deebot_client.commands.json.fan_speed import GetFanSpeed, SetFanSpeed
from deebot_client.commands.json.life_span import GetLifeSpan, ResetLifeSpan
from deebot_client.commands.json.map import GetCachedMapInfo, GetMajorMap, GetMapTrace
from deebot_client.commands.json.multimap_state import (
    GetMultimapState,
    SetMultimapState,
)
from deebot_client.commands.json.play_sound import PlaySound
from deebot_client.commands.json.pos import GetPos
from deebot_client.commands.json.relocation import SetRelocationState
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.commands.json.true_detect import GetTrueDetect, SetTrueDetect
from deebot_client.commands.json.volume import GetVolume, SetVolume
from deebot_client.commands.json.water_info import GetWaterInfo, SetWaterInfo
from deebot_client.const import DataType
from deebot_client.events import (
    AdvancedModeEvent,
    AvailabilityEvent,
    BatteryEvent,
    CarpetAutoFanBoostEvent,
    CleanCountEvent,
    CleanLogEvent,
    CleanPreferenceEvent,
    ContinuousCleaningEvent,
    ErrorEvent,
    LifeSpan,
    LifeSpanEvent,
    MultimapStateEvent,
    RoomsEvent,
    StateEvent,
    StatsEvent,
    TotalStatsEvent,
    TrueDetectEvent,
    VolumeEvent,
)
from deebot_client.events.fan_speed import FanSpeedEvent
from deebot_client.events.map import (
    CachedMapInfoEvent,
    MajorMapEvent,
    MapTraceEvent,
    PositionsEvent,
)
from deebot_client.events.water_info import WaterAmount, WaterInfoEvent
from deebot_client.models import StaticDeviceInfo

from . import DEVICES, FALLBACK

DEVICES[FALLBACK] = StaticDeviceInfo(
    DataType.JSON,
    Capabilities(
        availability=CapabilityEvent(AvailabilityEvent, [GetBattery(True)]),
        battery=CapabilityEvent(BatteryEvent, [GetBattery()]),
        charge=CapabilityExecute(Charge),
        clean=CapabilityClean(
            action=CapabilityCleanAction(command=Clean, area=CleanArea),
            continuous=CapabilitySetEnable(
                ContinuousCleaningEvent,
                [GetContinuousCleaning()],
                SetContinuousCleaning,
            ),
            count=CapabilitySet[int](CleanCountEvent, [GetCleanCount()], SetCleanCount),
            log=CapabilityEvent(CleanLogEvent, [GetCleanLogs()]),
            preference=CapabilitySetEnable(
                CleanPreferenceEvent, [GetCleanPreference()], SetCleanPreference
            ),
        ),
        error=CapabilityEvent(ErrorEvent, [GetError()]),
        fan_speed=CapabilitySet(FanSpeedEvent, [GetFanSpeed()], SetFanSpeed),
        life_span=CapabilityLifeSpan(
            types={LifeSpan.BRUSH, LifeSpan.FILTER, LifeSpan.SIDE_BRUSH},
            event=LifeSpanEvent,
            get=[GetLifeSpan([LifeSpan.BRUSH, LifeSpan.FILTER, LifeSpan.SIDE_BRUSH])],
            reset=ResetLifeSpan,
        ),
        map=CapabilityMap(
            chached_info=CapabilityEvent(CachedMapInfoEvent, [GetCachedMapInfo()]),
            major=CapabilityEvent(MajorMapEvent, [GetMajorMap()]),
            multi_state=CapabilitySetEnable(
                MultimapStateEvent, [GetMultimapState()], SetMultimapState
            ),
            position=CapabilityEvent(PositionsEvent, [GetPos()]),
            relocation=CapabilityExecute(SetRelocationState),
            rooms=CapabilityEvent(RoomsEvent, [GetCachedMapInfo()]),
            trace=CapabilityEvent(MapTraceEvent, [GetMapTrace()]),
        ),
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
            true_detect=CapabilitySetEnable(
                TrueDetectEvent, [GetTrueDetect()], SetTrueDetect
            ),
            volume=CapabilitySet[int](VolumeEvent, [GetVolume()], SetVolume),
        ),
        state=CapabilityEvent(StateEvent, [GetChargeState(), GetCleanInfo()]),
        stats=CapabilityStats(
            clean=CapabilityEvent(StatsEvent, [GetStats()]),
            total=CapabilityEvent(TotalStatsEvent, [GetTotalStats()]),
        ),
        water=CapabilitySet[WaterAmount](
            WaterInfoEvent, [GetWaterInfo()], SetWaterInfo
        ),
    ),
)
