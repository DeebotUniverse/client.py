from __future__ import annotations

from deebot_client import hardware
from deebot_client.commands import StationAction
from deebot_client.commands.json import station_action
from deebot_client.commands.json.advanced_mode import GetAdvancedMode
from deebot_client.commands.json.auto_empty import GetAutoEmpty
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.border_spin import GetBorderSpin
from deebot_client.commands.json.carpet import GetCarpetAutoFanBoost
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.child_lock import GetChildLock
from deebot_client.commands.json.clean import GetCleanInfoV2
from deebot_client.commands.json.clean_count import GetCleanCount
from deebot_client.commands.json.clean_logs import GetCleanLogs
from deebot_client.commands.json.clean_preference import GetCleanPreference
from deebot_client.commands.json.continuous_cleaning import GetContinuousCleaning
from deebot_client.commands.json.efficiency import GetEfficiencyMode
from deebot_client.commands.json.error import GetError
from deebot_client.commands.json.fan_speed import GetFanSpeed
from deebot_client.commands.json.life_span import GetLifeSpan
from deebot_client.commands.json.map import GetCachedMapInfo, GetMajorMap, GetMapTrace
from deebot_client.commands.json.multimap_state import GetMultimapState
from deebot_client.commands.json.network import GetNetInfo
from deebot_client.commands.json.ota import GetOta
from deebot_client.commands.json.pos import GetPos
from deebot_client.commands.json.station_state import GetStationState
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.commands.json.sweep_mode import GetSweepMode
from deebot_client.commands.json.true_detect import GetTrueDetect
from deebot_client.commands.json.voice_assistant_state import GetVoiceAssistantState
from deebot_client.commands.json.volume import GetVolume
from deebot_client.commands.json.water_info import GetWaterInfo
from deebot_client.events import (
    AdvancedModeEvent,
    AutoEmptyEvent,
    AvailabilityEvent,
    BatteryEvent,
    BorderSpinEvent,
    CachedMapInfoEvent,
    CarpetAutoFanBoostEvent,
    ChildLockEvent,
    CleanCountEvent,
    CleanLogEvent,
    CleanPreferenceEvent,
    ContinuousCleaningEvent,
    CustomCommandEvent,
    ErrorEvent,
    FanSpeedEvent,
    LifeSpan,
    LifeSpanEvent,
    MajorMapEvent,
    MapChangedEvent,
    MapTraceEvent,
    MultimapStateEvent,
    NetworkInfoEvent,
    OtaEvent,
    PositionsEvent,
    ReportStatsEvent,
    RoomsEvent,
    StateEvent,
    StationEvent,
    StatsEvent,
    SweepModeEvent,
    TotalStatsEvent,
    TrueDetectEvent,
    VoiceAssistantStateEvent,
    VolumeEvent,
    auto_empty,
)
from deebot_client.events.efficiency_mode import EfficiencyModeEvent
from deebot_client.events.water_info import MopAttachedEvent, WaterAmountEvent

# Consumables the X1 OMNI reports (superset of the X1 Turbo profile).
LIFE_SPANS = (
    LifeSpan.BRUSH,
    LifeSpan.FILTER,
    LifeSpan.SIDE_BRUSH,
    LifeSpan.UNIT_CARE,
    LifeSpan.ROUND_MOP,
    LifeSpan.AIR_FRESHENER,
    LifeSpan.DUST_BAG,
    LifeSpan.STRAINER,
)

# Complete refreshable-event -> commands map for class 1vxt52 (DEEBOT X1 OMNI).
EXPECTED_REFRESH_COMMANDS = {
    AdvancedModeEvent: [GetAdvancedMode()],
    AutoEmptyEvent: [GetAutoEmpty()],
    AvailabilityEvent: [GetBattery(is_available_check=True)],
    BatteryEvent: [GetBattery()],
    BorderSpinEvent: [GetBorderSpin()],
    CachedMapInfoEvent: [GetCachedMapInfo()],
    CarpetAutoFanBoostEvent: [GetCarpetAutoFanBoost()],
    ChildLockEvent: [GetChildLock()],
    CleanCountEvent: [GetCleanCount()],
    CleanLogEvent: [GetCleanLogs()],
    CleanPreferenceEvent: [GetCleanPreference()],
    ContinuousCleaningEvent: [GetContinuousCleaning()],
    CustomCommandEvent: [],
    EfficiencyModeEvent: [GetEfficiencyMode()],
    ErrorEvent: [GetError()],
    FanSpeedEvent: [GetFanSpeed()],
    LifeSpanEvent: [GetLifeSpan(list(LIFE_SPANS))],
    MajorMapEvent: [GetMajorMap()],
    MapChangedEvent: [],
    MapTraceEvent: [GetMapTrace()],
    MopAttachedEvent: [GetWaterInfo()],
    MultimapStateEvent: [GetMultimapState()],
    NetworkInfoEvent: [GetNetInfo()],
    OtaEvent: [GetOta()],
    PositionsEvent: [GetPos()],
    ReportStatsEvent: [],
    RoomsEvent: [GetCachedMapInfo()],
    StateEvent: [GetChargeState(), GetCleanInfoV2()],
    StationEvent: [GetStationState()],
    StatsEvent: [GetStats()],
    SweepModeEvent: [GetSweepMode()],
    TotalStatsEvent: [GetTotalStats()],
    TrueDetectEvent: [GetTrueDetect()],
    VoiceAssistantStateEvent: [GetVoiceAssistantState()],
    VolumeEvent: [GetVolume()],
    WaterAmountEvent: [GetWaterInfo()],
}


async def test_1vxt52_refresh_command_map() -> None:
    """Pin every refreshable event and its commands (exhaustive)."""
    info = await hardware.get_static_device_info("1vxt52")
    assert info is not None
    capabilities = info.capabilities

    assert capabilities._events.keys() == EXPECTED_REFRESH_COMMANDS.keys()
    for event, commands in EXPECTED_REFRESH_COMMANDS.items():
        assert capabilities.get_refresh_commands(event) == commands, event


async def test_1vxt52_omni_additions() -> None:
    """The capabilities added on top of the X1 Turbo profile."""
    info = await hardware.get_static_device_info("1vxt52")
    assert info is not None
    capabilities = info.capabilities

    assert capabilities.station is not None
    assert capabilities.station.action.execute is station_action.StationAction
    assert capabilities.station.action.types == (
        StationAction.EMPTY_DUSTBIN,
        StationAction.DRY_MOP,
        StationAction.WASH_MOP,
    )
    assert capabilities.station.auto_empty.types == (
        auto_empty.Frequency.AUTO,
        auto_empty.Frequency.SMART,
    )

    assert capabilities.life_span.types == LIFE_SPANS

    assert capabilities.settings.child_lock is not None
    assert capabilities.settings.border_spin is not None
    assert capabilities.settings.efficiency_mode is not None
    assert capabilities.settings.ota is not None


async def test_x1_turbo_profile_stays_station_less() -> None:
    """The shared X1 Turbo profile must not gain the X1 OMNI's station."""
    info = await hardware.get_static_device_info("2o4lnm")
    assert info is not None
    assert info.capabilities.station is None
