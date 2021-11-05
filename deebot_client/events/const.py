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
    PositionsEventDto,
    ReportStatsEventDto,
    RoomsEventDto,
    StatsEventDto,
    StatusEventDto,
    TotalStatsEventDto,
    VolumeEventDto,
    WaterInfoEventDto,
)
from .map import MajorMapEventDto, MapSetEventDto, MapTraceEventDto

EVENT_DTO_REFRESH_COMMANDS: Mapping[Type[EventDto], List[Command]] = {
    BatteryEventDto: [GetBattery()],
    CleanLogEventDto: [GetCleanLogs()],
    CustomCommandEventDto: [],
    ErrorEventDto: [GetError()],
    FanSpeedEventDto: [GetFanSpeed()],
    LifeSpanEventDto: [GetLifeSpan()],
    MajorMapEventDto: [GetMajorMap()],
    MapEventDto: [GetMapTrace(), GetPos(), GetMajorMap()],
    MapSetEventDto: [],
    MapTraceEventDto: [GetMapTrace()],
    PositionsEventDto: [GetPos()],
    ReportStatsEventDto: [],  # ReportStats cannot be pulled
    RoomsEventDto: [GetCachedMapInfo()],
    StatsEventDto: [GetStats()],
    StatusEventDto: [GetChargeState(), GetCleanInfo()],
    TotalStatsEventDto: [GetTotalStats()],
    VolumeEventDto: [GetVolume()],
    WaterInfoEventDto: [GetWaterInfo()],
}
