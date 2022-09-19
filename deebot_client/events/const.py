"""Event constants."""
from collections.abc import Mapping

from ..command import Command
from ..command_old import CommandOld
from ..commands import (
    GetAdvancedMode,
    GetBattery,
    GetCachedMapInfo,
    GetCarpetAutoFanBoost,
    GetChargeState,
    GetCleanInfo,
    GetCleanLogs,
    GetContinuousCleaning,
    GetError,
    GetFanSpeed,
    GetLifeSpan,
    GetMajorMap,
    GetMapTrace,
    GetPos,
    GetStats,
    GetTotalStats,
    GetVolume,
    GetWaterInfo,
)
from . import (
    AdvancedModeEvent,
    BatteryEvent,
    CarpetAutoFanBoostEvent,
    CleanLogEvent,
    ContinuousCleaningEvent,
    CustomCommandEvent,
    ErrorEvent,
    Event,
    FanSpeedEvent,
    LifeSpanEvent,
    PositionsEvent,
    ReportStatsEvent,
    RoomsEvent,
    StatsEvent,
    StatusEvent,
    TotalStatsEvent,
    VolumeEvent,
    WaterInfoEvent,
)
from .map import (
    MajorMapEvent,
    MapSetEvent,
    MapSubsetEvent,
    MapTraceEvent,
    MinorMapEvent,
)

EVENT_DTO_REFRESH_COMMANDS: Mapping[type[Event], list[Command | CommandOld]] = {
    AdvancedModeEvent: [GetAdvancedMode()],
    BatteryEvent: [GetBattery()],
    CarpetAutoFanBoostEvent: [GetCarpetAutoFanBoost()],
    CleanLogEvent: [GetCleanLogs()],
    ContinuousCleaningEvent: [GetContinuousCleaning()],
    CustomCommandEvent: [],
    ErrorEvent: [GetError()],
    FanSpeedEvent: [GetFanSpeed()],
    LifeSpanEvent: [GetLifeSpan()],
    MajorMapEvent: [GetMajorMap()],
    MapSetEvent: [],
    MapSubsetEvent: [],
    MapTraceEvent: [GetMapTrace()],
    MinorMapEvent: [],
    PositionsEvent: [GetPos()],
    ReportStatsEvent: [],  # ReportStats cannot be pulled
    RoomsEvent: [GetCachedMapInfo()],
    StatsEvent: [GetStats()],
    StatusEvent: [GetChargeState(), GetCleanInfo()],
    TotalStatsEvent: [GetTotalStats()],
    VolumeEvent: [GetVolume()],
    WaterInfoEvent: [GetWaterInfo()],
}
