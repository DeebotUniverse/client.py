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
    BatteryEvent,
    CleanLogEvent,
    CustomCommandEvent,
    ErrorEvent,
    Event,
    FanSpeedEvent,
    LifeSpanEvent,
    PositionsEvent,
    ReportStatsEvent,
    RoomEvent,
    RoomsEvent,
    StatsEvent,
    StatusEvent,
    TotalStatsEvent,
    VolumeEvent,
    WaterInfoEvent,
)
from .map import MajorMapEvent, MapSetEvent, MapTraceEvent, MinorMapEvent

EVENT_DTO_REFRESH_COMMANDS: Mapping[Type[Event], List[Command]] = {
    BatteryEvent: [GetBattery()],
    CleanLogEvent: [GetCleanLogs()],
    CustomCommandEvent: [],
    ErrorEvent: [GetError()],
    FanSpeedEvent: [GetFanSpeed()],
    LifeSpanEvent: [GetLifeSpan()],
    MajorMapEvent: [GetMajorMap()],
    MapSetEvent: [],
    MapTraceEvent: [GetMapTrace()],
    MinorMapEvent: [],
    PositionsEvent: [GetPos()],
    ReportStatsEvent: [],  # ReportStats cannot be pulled
    RoomEvent: [],
    RoomsEvent: [GetCachedMapInfo()],
    StatsEvent: [GetStats()],
    StatusEvent: [GetChargeState(), GetCleanInfo()],
    TotalStatsEvent: [GetTotalStats()],
    VolumeEvent: [GetVolume()],
    WaterInfoEvent: [GetWaterInfo()],
}
