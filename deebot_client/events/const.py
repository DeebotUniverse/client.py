"""Event constants."""
from typing import List, Mapping, Type

from ..command import Command
from ..commands import (
    GetBattery,
    GetCachedMapInfo,
    GetChargeState,
    GetCleanInfo,
    GetCleanLogs,
    GetError,
    GetFanSpeed,
    GetLifeSpan,
    GetMajorMap,
    GetMapTrace,
    GetPos,
    GetStats,
    GetVolume,
    GetWaterInfo,
)
from ..commands.stats import GetTotalStats
from . import (
    BatteryEventDto,
    CleanLogEventDto,
    CustomCommandEventDto,
    ErrorEventDto,
    EventDto,
    FanSpeedEventDto,
    LifeSpanEventDto,
    MapEventDto,
    ReportStatsEventDto,
    RoomsEventDto,
    StatsEventDto,
    StatusEventDto,
    TotalStatsEventDto,
    VolumeEventDto,
    WaterInfoEventDto,
)

EVENT_DTO_REFRESH_COMMANDS: Mapping[Type[EventDto], List[Command]] = {
    BatteryEventDto: [GetBattery()],
    CleanLogEventDto: [GetCleanLogs()],
    CustomCommandEventDto: [],
    ErrorEventDto: [GetError()],
    FanSpeedEventDto: [GetFanSpeed()],
    LifeSpanEventDto: [GetLifeSpan()],
    MapEventDto: [GetMapTrace(), GetPos(), GetMajorMap()],
    ReportStatsEventDto: [],  # ReportStats cannot be pulled
    RoomsEventDto: [GetCachedMapInfo()],
    StatsEventDto: [GetStats()],
    StatusEventDto: [GetChargeState(), GetCleanInfo()],
    TotalStatsEventDto: [GetTotalStats()],
    VolumeEventDto: [GetVolume()],
    WaterInfoEventDto: [GetWaterInfo()],
}
