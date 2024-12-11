"""Hardware init tests."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from deebot_client.commands.json import GetCutDirection
from deebot_client.commands.json.advanced_mode import GetAdvancedMode
from deebot_client.commands.json.auto_empty import GetAutoEmpty
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.border_switch import GetBorderSwitch
from deebot_client.commands.json.carpet import GetCarpetAutoFanBoost
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.child_lock import GetChildLock
from deebot_client.commands.json.clean import GetCleanInfo, GetCleanInfoV2
from deebot_client.commands.json.clean_count import GetCleanCount
from deebot_client.commands.json.clean_logs import GetCleanLogs
from deebot_client.commands.json.clean_preference import GetCleanPreference
from deebot_client.commands.json.continuous_cleaning import GetContinuousCleaning
from deebot_client.commands.json.cross_map_border_warning import (
    GetCrossMapBorderWarning,
)
from deebot_client.commands.json.efficiency import GetEfficiencyMode
from deebot_client.commands.json.error import GetError
from deebot_client.commands.json.fan_speed import GetFanSpeed
from deebot_client.commands.json.life_span import GetLifeSpan
from deebot_client.commands.json.map import GetCachedMapInfo, GetMajorMap, GetMapTrace
from deebot_client.commands.json.moveup_warning import GetMoveUpWarning
from deebot_client.commands.json.multimap_state import GetMultimapState
from deebot_client.commands.json.network import GetNetInfo
from deebot_client.commands.json.ota import GetOta
from deebot_client.commands.json.pos import GetPos
from deebot_client.commands.json.safe_protect import GetSafeProtect
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.commands.json.true_detect import GetTrueDetect
from deebot_client.commands.json.voice_assistant_state import GetVoiceAssistantState
from deebot_client.commands.json.volume import GetVolume
from deebot_client.commands.json.water_info import GetWaterInfo
from deebot_client.events import (
    AdvancedModeEvent,
    AvailabilityEvent,
    BatteryEvent,
    BorderSwitchEvent,
    CarpetAutoFanBoostEvent,
    ChildLockEvent,
    CleanCountEvent,
    CleanLogEvent,
    CleanPreferenceEvent,
    ContinuousCleaningEvent,
    CrossMapBorderWarningEvent,
    CustomCommandEvent,
    CutDirectionEvent,
    ErrorEvent,
    LifeSpan,
    LifeSpanEvent,
    MoveUpWarningEvent,
    MultimapStateEvent,
    OtaEvent,
    ReportStatsEvent,
    RoomsEvent,
    SafeProtectEvent,
    StateEvent,
    StatsEvent,
    TotalStatsEvent,
    TrueDetectEvent,
    VoiceAssistantStateEvent,
    VolumeEvent,
    auto_empty,
)
from deebot_client.events.efficiency_mode import EfficiencyModeEvent
from deebot_client.events.fan_speed import FanSpeedEvent
from deebot_client.events.map import (
    CachedMapInfoEvent,
    MajorMapEvent,
    MapChangedEvent,
    MapTraceEvent,
    PositionsEvent,
)
from deebot_client.events.network import NetworkInfoEvent
from deebot_client.events.water_info import WaterInfoEvent
from deebot_client.hardware import deebot as hardware_deebot, get_static_device_info

if TYPE_CHECKING:
    from collections.abc import Callable

    from deebot_client.command import Command
    from deebot_client.events.base import Event
    from deebot_client.models import StaticDeviceInfo


@pytest.mark.parametrize(
    ("class_", "expected"),
    [
        ("not_specified", lambda: None),
        ("yna5xi", lambda: hardware_deebot.DEVICES["yna5xi"]),
    ],
)
async def test_get_static_device_info(
    class_: str, expected: Callable[[], StaticDeviceInfo]
) -> None:
    """Test get_static_device_info."""
    static_device_info = await get_static_device_info(class_)
    assert static_device_info == expected()


@pytest.mark.parametrize(
    ("class_", "expected"),
    [
        (
            "5xu9h3",
            {
                AdvancedModeEvent: [GetAdvancedMode()],
                AvailabilityEvent: [GetBattery(is_available_check=True)],
                BatteryEvent: [GetBattery()],
                BorderSwitchEvent: [GetBorderSwitch()],
                CutDirectionEvent: [GetCutDirection()],
                ChildLockEvent: [GetChildLock()],
                CrossMapBorderWarningEvent: [GetCrossMapBorderWarning()],
                CustomCommandEvent: [],
                ErrorEvent: [GetError()],
                LifeSpanEvent: [GetLifeSpan([LifeSpan.BLADE, LifeSpan.LENS_BRUSH])],
                MoveUpWarningEvent: [GetMoveUpWarning()],
                NetworkInfoEvent: [GetNetInfo()],
                ReportStatsEvent: [],
                SafeProtectEvent: [GetSafeProtect()],
                StateEvent: [GetChargeState(), GetCleanInfoV2()],
                StatsEvent: [GetStats()],
                TotalStatsEvent: [GetTotalStats()],
                TrueDetectEvent: [GetTrueDetect()],
                VolumeEvent: [GetVolume()],
            },
        ),
        (
            "itk04l",
            {
                AdvancedModeEvent: [GetAdvancedMode()],
                AvailabilityEvent: [GetBattery(is_available_check=True)],
                BatteryEvent: [GetBattery()],
                BorderSwitchEvent: [GetBorderSwitch()],
                CutDirectionEvent: [GetCutDirection()],
                ChildLockEvent: [GetChildLock()],
                CrossMapBorderWarningEvent: [GetCrossMapBorderWarning()],
                CustomCommandEvent: [],
                ErrorEvent: [GetError()],
                LifeSpanEvent: [GetLifeSpan([LifeSpan.BLADE, LifeSpan.LENS_BRUSH])],
                MoveUpWarningEvent: [GetMoveUpWarning()],
                NetworkInfoEvent: [GetNetInfo()],
                ReportStatsEvent: [],
                SafeProtectEvent: [GetSafeProtect()],
                StateEvent: [GetChargeState(), GetCleanInfoV2()],
                StatsEvent: [GetStats()],
                TotalStatsEvent: [GetTotalStats()],
                TrueDetectEvent: [GetTrueDetect()],
                VolumeEvent: [GetVolume()],
            },
        ),
        (
            "yna5xi",
            {
                AdvancedModeEvent: [GetAdvancedMode()],
                AvailabilityEvent: [GetBattery(is_available_check=True)],
                BatteryEvent: [GetBattery()],
                CachedMapInfoEvent: [GetCachedMapInfo()],
                CarpetAutoFanBoostEvent: [GetCarpetAutoFanBoost()],
                CleanLogEvent: [GetCleanLogs()],
                ContinuousCleaningEvent: [GetContinuousCleaning()],
                CustomCommandEvent: [],
                ErrorEvent: [GetError()],
                FanSpeedEvent: [GetFanSpeed()],
                LifeSpanEvent: [
                    GetLifeSpan([LifeSpan.BRUSH, LifeSpan.FILTER, LifeSpan.SIDE_BRUSH])
                ],
                MapChangedEvent: [],
                MajorMapEvent: [GetMajorMap()],
                MapTraceEvent: [GetMapTrace()],
                MultimapStateEvent: [GetMultimapState()],
                NetworkInfoEvent: [GetNetInfo()],
                OtaEvent: [GetOta()],
                PositionsEvent: [GetPos()],
                ReportStatsEvent: [],
                RoomsEvent: [GetCachedMapInfo()],
                StateEvent: [GetChargeState(), GetCleanInfo()],
                StatsEvent: [GetStats()],
                TotalStatsEvent: [GetTotalStats()],
                VolumeEvent: [GetVolume()],
                WaterInfoEvent: [GetWaterInfo()],
            },
        ),
        (
            "p95mgv",
            {
                auto_empty.Event: [GetAutoEmpty()],
                AdvancedModeEvent: [GetAdvancedMode()],
                AvailabilityEvent: [GetBattery(is_available_check=True)],
                BatteryEvent: [GetBattery()],
                CachedMapInfoEvent: [GetCachedMapInfo()],
                CarpetAutoFanBoostEvent: [GetCarpetAutoFanBoost()],
                CleanCountEvent: [GetCleanCount()],
                CleanPreferenceEvent: [GetCleanPreference()],
                ContinuousCleaningEvent: [GetContinuousCleaning()],
                CustomCommandEvent: [],
                EfficiencyModeEvent: [GetEfficiencyMode()],
                ErrorEvent: [GetError()],
                FanSpeedEvent: [GetFanSpeed()],
                LifeSpanEvent: [
                    GetLifeSpan(
                        [
                            LifeSpan.BRUSH,
                            LifeSpan.FILTER,
                            LifeSpan.SIDE_BRUSH,
                            LifeSpan.UNIT_CARE,
                        ]
                    )
                ],
                MajorMapEvent: [GetMajorMap()],
                MapChangedEvent: [],
                MapTraceEvent: [GetMapTrace()],
                MultimapStateEvent: [GetMultimapState()],
                NetworkInfoEvent: [GetNetInfo()],
                OtaEvent: [GetOta()],
                PositionsEvent: [GetPos()],
                ReportStatsEvent: [],
                RoomsEvent: [GetCachedMapInfo()],
                StateEvent: [GetChargeState(), GetCleanInfo()],
                StatsEvent: [GetStats()],
                TotalStatsEvent: [GetTotalStats()],
                TrueDetectEvent: [GetTrueDetect()],
                VoiceAssistantStateEvent: [GetVoiceAssistantState()],
                VolumeEvent: [GetVolume()],
                WaterInfoEvent: [GetWaterInfo()],
            },
        ),
    ],
    ids=["5xu9h3", "itk04l", "yna5xi", "p95mgv"],
)
async def test_capabilities_event_extraction(
    class_: str, expected: dict[type[Event], list[Command]]
) -> None:
    info = await get_static_device_info(class_)
    assert info is not None
    capabilities = info.capabilities
    assert capabilities._events.keys() == expected.keys()
    for event, expected_commands in expected.items():
        assert (
            capabilities.get_refresh_commands(event) == expected_commands
        ), f"Refresh commands doesn't match for {event}"


def test_all_models_loaded() -> None:
    """Test that all models are loaded."""
    hardware_deebot._load()
    folder = Path(hardware_deebot.__file__).parent
    assert list(hardware_deebot.DEVICES) == sorted(
        [
            name.removesuffix(".py")
            for name in os.listdir(folder)
            if (folder / name).is_file() and name != "__init__.py"
        ]
    )
