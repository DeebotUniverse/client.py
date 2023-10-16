"""Hardware init tests."""


from collections.abc import Callable

import pytest

from deebot_client.capabilities import Capabilities
from deebot_client.command import Command
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
from deebot_client.events.base import Event
from deebot_client.events.fan_speed import FanSpeedEvent
from deebot_client.events.map import (
    CachedMapInfoEvent,
    MajorMapEvent,
    MapTraceEvent,
    PositionsEvent,
)
from deebot_client.events.water_info import WaterInfoEvent
from deebot_client.hardware import get_capabilities
from deebot_client.hardware.deebot import DEVICES, FALLBACK


@pytest.mark.parametrize(
    "_class, expected",
    [
        ("not_specified", lambda: DEVICES[FALLBACK]),
        ("yna5x1", lambda: DEVICES["yna5x1"]),
    ],
)
def test_get_capabilities(_class: str, expected: Callable[[], Capabilities]) -> None:
    """Test get_capabilities."""
    capabilities = get_capabilities(_class)
    assert expected() == capabilities


@pytest.mark.parametrize(
    "class_, expected",
    [
        (
            FALLBACK,
            {
                AdvancedModeEvent: [GetAdvancedMode()],
                AvailabilityEvent: [GetBattery(True)],
                BatteryEvent: [GetBattery()],
                CachedMapInfoEvent: [GetCachedMapInfo()],
                CarpetAutoFanBoostEvent: [GetCarpetAutoFanBoost()],
                CleanCountEvent: [GetCleanCount()],
                CleanLogEvent: [GetCleanLogs()],
                CleanPreferenceEvent: [GetCleanPreference()],
                ContinuousCleaningEvent: [GetContinuousCleaning()],
                ErrorEvent: [GetError()],
                FanSpeedEvent: [GetFanSpeed()],
                LifeSpanEvent: [
                    GetLifeSpan([LifeSpan.BRUSH, LifeSpan.FILTER, LifeSpan.SIDE_BRUSH])
                ],
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
        ),
        (
            "yna5x1",
            {
                AdvancedModeEvent: [GetAdvancedMode()],
                AvailabilityEvent: [GetBattery(True)],
                BatteryEvent: [GetBattery()],
                CachedMapInfoEvent: [GetCachedMapInfo()],
                CarpetAutoFanBoostEvent: [GetCarpetAutoFanBoost()],
                CleanLogEvent: [GetCleanLogs()],
                ContinuousCleaningEvent: [GetContinuousCleaning()],
                ErrorEvent: [GetError()],
                FanSpeedEvent: [GetFanSpeed()],
                LifeSpanEvent: [
                    GetLifeSpan([LifeSpan.BRUSH, LifeSpan.FILTER, LifeSpan.SIDE_BRUSH])
                ],
                MajorMapEvent: [GetMajorMap()],
                MapTraceEvent: [GetMapTrace()],
                MultimapStateEvent: [GetMultimapState()],
                PositionsEvent: [GetPos()],
                RoomsEvent: [GetCachedMapInfo()],
                StateEvent: [GetChargeState(), GetCleanInfo()],
                StatsEvent: [GetStats()],
                TotalStatsEvent: [GetTotalStats()],
                VolumeEvent: [GetVolume()],
                WaterInfoEvent: [GetWaterInfo()],
            },
        ),
    ],
)
def test_capabilities_event_extraction(
    class_: str, expected: dict[type[Event], list[Command]]
) -> None:
    capabilities = get_capabilities(class_)
    assert capabilities._events.keys() == expected.keys()
    for event, expected_commands in expected.items():
        assert capabilities.get_refresh_commands(event) == expected_commands
