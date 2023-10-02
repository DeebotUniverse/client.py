"""Deebot devices."""

from collections.abc import Mapping

from deebot_client.commands.json.advanced_mode import GetAdvancedMode
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.carpet import GetCarpetAutoFanBoost
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.clean import GetCleanInfo
from deebot_client.commands.json.clean_logs import GetCleanLogs
from deebot_client.commands.json.continuous_cleaning import GetContinuousCleaning
from deebot_client.commands.json.error import GetError
from deebot_client.commands.json.fan_speed import GetFanSpeed
from deebot_client.commands.json.life_span import GetLifeSpan
from deebot_client.commands.json.map import GetCachedMapInfo, GetMajorMap, GetMapTrace
from deebot_client.commands.json.multimap_state import GetMultimapState
from deebot_client.commands.json.pos import GetPos
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.commands.json.true_detect import GetTrueDetect
from deebot_client.commands.json.volume import GetVolume
from deebot_client.commands.json.water_info import GetWaterInfo
from deebot_client.events import (
    AdvancedModeEvent,
    AvailabilityEvent,
    BatteryEvent,
    CarpetAutoFanBoostEvent,
    CleanLogEvent,
    ContinuousCleaningEvent,
    CustomCommandEvent,
    ErrorEvent,
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
from deebot_client.events.water_info import WaterInfoEvent
from deebot_client.hardware.device_capabilities import DeviceCapabilities

DEVICES: Mapping[str, DeviceCapabilities] = {
    "yna5x1": DeviceCapabilities(
        "Deebot Ozmo 950",
        {
            AdvancedModeEvent: [GetAdvancedMode()],
            AvailabilityEvent: [GetBattery(True)],
            BatteryEvent: [GetBattery()],
            CachedMapInfoEvent: [GetCachedMapInfo()],
            CarpetAutoFanBoostEvent: [GetCarpetAutoFanBoost()],
            CleanLogEvent: [GetCleanLogs()],
            ContinuousCleaningEvent: [GetContinuousCleaning()],
            CustomCommandEvent: [],
            ErrorEvent: [GetError()],
            FanSpeedEvent: [GetFanSpeed()],
            LifeSpanEvent: [GetLifeSpan()],
            MajorMapEvent: [GetMajorMap()],
            MapTraceEvent: [GetMapTrace()],
            MultimapStateEvent: [GetMultimapState()],
            PositionsEvent: [GetPos()],
            RoomsEvent: [GetCachedMapInfo()],
            StateEvent: [GetChargeState(), GetCleanInfo()],
            StatsEvent: [GetStats()],
            TotalStatsEvent: [GetTotalStats()],
            TrueDetectEvent: [GetTrueDetect()],
            VolumeEvent: [GetVolume()],
            WaterInfoEvent: [GetWaterInfo()],
        },
    )
}
