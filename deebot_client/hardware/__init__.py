"""Hardware module."""


from deebot_client.commands.json.advanced_mode import GetAdvancedMode
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.carpet import GetCarpetAutoFanBoost
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.clean import GetCleanInfo
from deebot_client.commands.json.clean_count import GetCleanCount
from deebot_client.commands.json.clean_logs import GetCleanLogs
from deebot_client.commands.json.clean_preference import GetCleanPreference
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
    CleanCountEvent,
    CleanLogEvent,
    CleanPreferenceEvent,
    ContinuousCleaningEvent,
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
from deebot_client.logging_filter import get_logger

from . import deebot

_LOGGER = get_logger(__name__)

_DEFAULT = DeviceCapabilities(
    "_default",
    {
        AvailabilityEvent: [GetBattery(True)],
        AdvancedModeEvent: [GetAdvancedMode()],
        BatteryEvent: [GetBattery()],
        CachedMapInfoEvent: [GetCachedMapInfo()],
        CarpetAutoFanBoostEvent: [GetCarpetAutoFanBoost()],
        CleanLogEvent: [GetCleanLogs()],
        CleanCountEvent: [GetCleanCount()],
        CleanPreferenceEvent: [GetCleanPreference()],
        ContinuousCleaningEvent: [GetContinuousCleaning()],
        ErrorEvent: [GetError()],
        FanSpeedEvent: [GetFanSpeed()],
        LifeSpanEvent: [GetLifeSpan()],
        MajorMapEvent: [GetMajorMap()],
        MapTraceEvent: [GetMapTrace()],
        MultimapStateEvent: [GetMultimapState()],
        PositionsEvent: [GetPos()],
        RoomsEvent: [GetCachedMapInfo()],
        StatsEvent: [GetStats()],
        StateEvent: [GetChargeState(), GetCleanInfo()],
        TotalStatsEvent: [GetTotalStats()],
        TrueDetectEvent: [GetTrueDetect()],
        VolumeEvent: [GetVolume()],
        WaterInfoEvent: [GetWaterInfo()],
    },
)


def get_device_capabilities(clazz: str) -> DeviceCapabilities:
    """Get device capabilities for given class."""
    if device := deebot.DEVICES.get(clazz):
        return device

    _LOGGER.debug("No device capabilities found for %s. Fallback to default.", clazz)
    return _DEFAULT
