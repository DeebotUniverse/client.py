"""Deebot 900 Capabilities."""
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
)
from deebot_client.commands.json.advanced_mode import GetAdvancedMode, SetAdvancedMode
from deebot_client.commands.json.carpet import (
    GetCarpetAutoFanBoost,
    SetCarpetAutoFanBoost,
)
from deebot_client.commands.json.charge import Charge
from deebot_client.commands.json.clean import Clean, CleanArea
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
from deebot_client.commands.json.custom import CustomCommand
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
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.commands.json.true_detect import GetTrueDetect, SetTrueDetect
from deebot_client.commands.json.volume import GetVolume, SetVolume
from deebot_client.commands.json.water_info import GetWaterInfo, SetWaterInfo
from deebot_client.commands.xml.battery import GetBattery
from deebot_client.commands.xml.charge_state import GetChargeState
from deebot_client.commands.xml.error import GetError
from deebot_client.commands.xml.fan_speed import GetFanSpeed
from deebot_client.const import DataType
from deebot_client.events import (
    AdvancedModeEvent,
    AvailabilityEvent,
    BatteryEvent,
    CachedMapInfoEvent,
    CarpetAutoFanBoostEvent,
    CleanCountEvent,
    CleanLogEvent,
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
    PositionsEvent,
    ReportStatsEvent,
    RoomsEvent,
    StateEvent,
    StatsEvent,
    TotalStatsEvent,
    TrueDetectEvent,
    VolumeEvent,
    WaterAmount,
    WaterInfoEvent,
)
from deebot_client.events.network import NetworkInfoEvent
from deebot_client.models import StaticDeviceInfo
from deebot_client.util import short_name

from ...commands.json import SetFanSpeed
from . import DEVICES

DEVICES[short_name(__name__)] = StaticDeviceInfo(
    DataType.XML,
    Capabilities(
        availability=CapabilityEvent(AvailabilityEvent, [GetBattery(True)]),
        battery=CapabilityEvent(BatteryEvent, [GetBattery()]),
        charge=CapabilityExecute(Charge),  # todo needs to be re-implemented
        clean=CapabilityClean(  # todo needs to be re-implemented
            action=CapabilityCleanAction(command=Clean, area=CleanArea),
            continuous=CapabilitySetEnable(
                ContinuousCleaningEvent,
                [GetContinuousCleaning()],
                SetContinuousCleaning,
            ),
            count=CapabilitySet(CleanCountEvent, [GetCleanCount()], SetCleanCount),
            log=CapabilityEvent(CleanLogEvent, [GetCleanLogs()]),
            preference=CapabilitySetEnable(
                CleanPreferenceEvent, [GetCleanPreference()], SetCleanPreference
            ),
        ),
        custom=CapabilityCustomCommand(  # todo needs to be re-implemented
            event=CustomCommandEvent, get=[], set=CustomCommand
        ),
        error=CapabilityEvent(ErrorEvent, [GetError()]),
        fan_speed=CapabilitySetTypes(  # todo needs to be re-implemented
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
        life_span=CapabilityLifeSpan(  # todo needs to be re-implemented
            types=(LifeSpan.BRUSH, LifeSpan.FILTER, LifeSpan.SIDE_BRUSH),
            event=LifeSpanEvent,
            get=[GetLifeSpan([LifeSpan.BRUSH, LifeSpan.FILTER, LifeSpan.SIDE_BRUSH])],
            reset=ResetLifeSpan,
        ),
        map=CapabilityMap(  # todo needs to be re-implemented
            chached_info=CapabilityEvent(CachedMapInfoEvent, [GetCachedMapInfo()]),
            changed=CapabilityEvent(MapChangedEvent, []),
            major=CapabilityEvent(MajorMapEvent, [GetMajorMap()]),
            multi_state=CapabilitySetEnable(
                MultimapStateEvent, [GetMultimapState()], SetMultimapState
            ),
            position=CapabilityEvent(PositionsEvent, [GetPos()]),
            relocation=CapabilityExecute(SetRelocationState),
            rooms=CapabilityEvent(RoomsEvent, [GetCachedMapInfo()]),
            trace=CapabilityEvent(MapTraceEvent, [GetMapTrace()]),
        ),
        network=CapabilityEvent(
            NetworkInfoEvent, [GetNetInfo()]
        ),  # todo needs to be re-implemented
        play_sound=CapabilityExecute(PlaySound),  # todo needs to be re-implemented
        settings=CapabilitySettings(  # todo needs to be re-implemented
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
            volume=CapabilitySet(VolumeEvent, [GetVolume()], SetVolume),
        ),
        state=CapabilityEvent(StateEvent, [GetChargeState()]),
        stats=CapabilityStats(  # todo needs to be re-implemented
            clean=CapabilityEvent(StatsEvent, [GetStats()]),
            report=CapabilityEvent(ReportStatsEvent, []),
            total=CapabilityEvent(TotalStatsEvent, [GetTotalStats()]),
        ),
        water=CapabilitySetTypes(  # todo needs to be re-implemented
            event=WaterInfoEvent,
            get=[GetWaterInfo()],
            set=SetWaterInfo,
            types=(
                WaterAmount.LOW,
                WaterAmount.MEDIUM,
                WaterAmount.HIGH,
                WaterAmount.ULTRAHIGH,
            ),
        ),
    ),
)
