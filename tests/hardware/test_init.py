"""Hardware init tests."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from deebot_client import hardware
from deebot_client.commands import StationAction
from deebot_client.commands.json import GetCutDirection
from deebot_client.commands.json.advanced_mode import GetAdvancedMode
from deebot_client.commands.json.auto_empty import GetAutoEmpty
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.border_switch import GetBorderSwitch
from deebot_client.commands.json.carpet import GetCarpetAutoFanBoost
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.child_lock import GetChildLock
from deebot_client.commands.json.clean import (
    CleanAreaV2,
    CleanV2,
    GetCleanInfo,
    GetCleanInfoV2,
)
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
from deebot_client.commands.json.xwk78e import (
    ChargeT80,
    CleanAreaV2FreeClean,
    GetAutoEmptyT80,
    GetCleanPreferenceT80,
    GetWashInfoT80,
    GetWorkStateT80,
    SetAutoEmptyV2,
    SetCleanPreferenceT80,
    SetTrueDetectV2,
    SetWashInfoT80,
    StationActionT80,
)
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
from deebot_client.events.xwk78e import AutoEmptyEventT80, WashMode
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


async def test_xwk78e_uses_t80_capabilities() -> None:
    """Test that the China T80 class resolves to the T80 capability profile."""
    static_device_info = await hardware.get_static_device_info("xwk78e")

    assert static_device_info is not None
    assert static_device_info.capabilities.clean is not None
    assert static_device_info.capabilities.clean.action.command is CleanV2
    assert static_device_info.capabilities.clean.action.area is CleanAreaV2FreeClean
    assert static_device_info.capabilities.clean.preference.get == [
        GetCleanPreferenceT80()
    ]
    assert static_device_info.capabilities.clean.preference.set is SetCleanPreferenceT80
    assert static_device_info.capabilities.charge.execute is ChargeT80
    assert static_device_info.capabilities.life_span is not None
    assert static_device_info.capabilities.life_span.get[0] == GetLifeSpan(
        [
            LifeSpan.BRUSH,
            LifeSpan.FILTER,
            LifeSpan.SIDE_BRUSH,
            LifeSpan.UNIT_CARE,
            LifeSpan.CLEANING_SOLUTION,
            LifeSpan.SEWAGE_BOX,
            LifeSpan.DUST_BAG,
            LifeSpan.ROUND_MOP,
            LifeSpan.WATER_SINK,
        ]
    )
    assert static_device_info.capabilities.station is not None
    assert static_device_info.capabilities.station.auto_empty is not None
    assert static_device_info.capabilities.station.auto_empty.set is SetAutoEmptyV2
    assert static_device_info.capabilities.station.auto_empty.event is AutoEmptyEventT80
    assert static_device_info.capabilities.station.auto_empty.get == [GetAutoEmptyT80()]
    assert static_device_info.capabilities.station.wash_mode.types == tuple(WashMode)
    assert static_device_info.capabilities.station.wash_mode.set is SetWashInfoT80
    assert static_device_info.capabilities.station.wash_mode.get == [GetWashInfoT80()]
    assert static_device_info.capabilities.station.action.execute is StationActionT80
    assert static_device_info.capabilities.station.action.types == (
        StationAction.EMPTY_DUSTBIN,
        StationAction.DRY_MOP,
        StationAction.CLEAN_BASE,
        StationAction.WASH_MOP,
    )
    assert static_device_info.capabilities.settings is not None
    assert static_device_info.capabilities.settings.true_detect is not None
    assert static_device_info.capabilities.settings.true_detect.set is SetTrueDetectV2
    assert static_device_info.capabilities.get_refresh_commands(StateEvent) == [
        GetChargeState(),
        GetCleanInfoV2(),
        GetWorkStateT80(),
    ]


async def test_xwk78e_does_not_modify_shared_t80_profile() -> None:
    """Ensure the shared T80 profile keeps upstream capabilities."""
    shared = import_module("deebot_client.hardware.9eamof").get_device_info()

    assert shared.capabilities.clean.action.command is CleanV2
    assert shared.capabilities.clean.action.area is CleanAreaV2
    assert shared.capabilities.clean.preference.get == [GetCleanPreference()]
    assert shared.capabilities.station.action.types == (StationAction.EMPTY_DUSTBIN,)
    assert shared.capabilities.state is not None
    assert shared.capabilities.get_refresh_commands(StateEvent) == [
        GetChargeState(),
        GetCleanInfoV2(),
    ]
    assert shared.capabilities.life_span is not None
    assert LifeSpan.DUST_BAG not in shared.capabilities.life_span.types
    assert LifeSpan.ROUND_MOP not in shared.capabilities.life_span.types
    assert LifeSpan.WATER_SINK not in shared.capabilities.life_span.types


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
