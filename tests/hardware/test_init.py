"""Hardware init tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from deebot_client import hardware
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
from deebot_client.commands.json.station_state import GetStationState
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.commands.json.true_detect import GetTrueDetect
from deebot_client.commands.json.voice_assistant_state import GetVoiceAssistantState
from deebot_client.commands.json.volume import GetVolume
from deebot_client.commands.json.water_info import GetWaterInfo
from deebot_client.events import (
    AdvancedModeEvent,
    AutoEmptyEvent,
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
    StationEvent,
    StatsEvent,
    TotalStatsEvent,
    TrueDetectEvent,
    VoiceAssistantStateEvent,
    VolumeEvent,
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
from deebot_client.events.water_info import MopAttachedEvent, WaterAmountEvent
from deebot_client.hardware.yna5xi import get_device_info as get_yna5xi_info
from deebot_client.models import StaticDeviceInfo

if TYPE_CHECKING:
    from deebot_client.command import Command
    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    ("class_", "expected"),
    [
        ("not_specified", None),
        ("yna5xi", get_yna5xi_info()),
    ],
)
async def test_get_static_device_info(
    class_: str, expected: StaticDeviceInfo | None
) -> None:
    """Test get_static_device_info."""
    static_device_info = await hardware.get_static_device_info(class_)
    assert static_device_info == expected

    # Test caching
    with mock.patch("deebot_client.hardware.importlib.import_module") as mock_import:
        static_device_info_cached = await hardware.get_static_device_info(class_)
        assert static_device_info_cached == expected
        mock_import.assert_not_called()


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
                MopAttachedEvent: [GetWaterInfo()],
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
                WaterAmountEvent: [GetWaterInfo()],
            },
        ),
        (
            "p95mgv",
            {
                AutoEmptyEvent: [GetAutoEmpty()],
                AdvancedModeEvent: [GetAdvancedMode()],
                AvailabilityEvent: [GetBattery(is_available_check=True)],
                StationEvent: [GetStationState()],
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
                MopAttachedEvent: [GetWaterInfo()],
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
                WaterAmountEvent: [GetWaterInfo()],
            },
        ),
    ],
    ids=["5xu9h3", "itk04l", "yna5xi", "p95mgv"],
)
async def test_capabilities_event_extraction(
    class_: str, expected: dict[type[Event], list[Command]]
) -> None:
    info = await hardware.get_static_device_info(class_)
    assert info is not None
    capabilities = info.capabilities
    assert capabilities._events.keys() == expected.keys()
    for event, expected_commands in expected.items():
        assert capabilities.get_refresh_commands(event) == expected_commands, (
            f"Refresh commands doesn't match for {event}"
        )


async def test_all_models_loaded() -> None:
    """Test that all models can be loaded."""
    folder = Path(hardware.__file__).parent
    all_modules = sorted(
        [
            file.name.removesuffix(".py")
            for file in folder.iterdir()
            if file.is_file() and file.name != "__init__.py"
        ]
    )

    # Try to load each module
    for module_name in all_modules:
        device_info = await hardware.get_static_device_info(module_name)
        assert isinstance(device_info, StaticDeviceInfo), (
            f"Failed to load device info for {module_name}"
        )
