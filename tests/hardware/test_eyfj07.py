from __future__ import annotations

from deebot_client.capabilities import DeviceType
from deebot_client.commands.ngiot.battery import GetBattery
from deebot_client.commands.ngiot.charge import Charge
from deebot_client.commands.ngiot.child_lock import GetChildLock, SetChildLock
from deebot_client.commands.ngiot.clean import Clean, GetCleanInfo
from deebot_client.commands.ngiot.custom import CustomCommand
from deebot_client.commands.ngiot.error import GetError
from deebot_client.commands.ngiot.fan_speed import GetFanSpeed, SetFanSpeed
from deebot_client.commands.ngiot.life_span import GetLifeSpan, ResetLifeSpan
from deebot_client.commands.ngiot.network import GetNetInfo
from deebot_client.commands.ngiot.play_sound import PlaySound
from deebot_client.commands.ngiot.stats import GetReportStats, GetStats, GetTotalStats
from deebot_client.commands.ngiot.volume import GetVolume, SetVolume
from deebot_client.events import (
    AvailabilityEvent,
    BatteryEvent,
    ChildLockEvent,
    CustomCommandEvent,
    ErrorEvent,
    FanSpeedEvent,
    FanSpeedLevel,
    LifeSpan,
    LifeSpanEvent,
    NetworkInfoEvent,
    ReportStatsEvent,
    StateEvent,
    StatsEvent,
    TotalStatsEvent,
    VolumeEvent,
)
from deebot_client.hardware.eyfj07 import get_device_info


def test_eyfj07_profile_is_non_map_ngiot_profile() -> None:
    info = get_device_info()
    capabilities = info.capabilities

    assert info.data_type.value == "j"
    assert capabilities.device_type is DeviceType.VACUUM
    assert capabilities.map is None
    assert capabilities.water is None
    assert capabilities.clean.action.area is None


def test_eyfj07_profile_exposes_non_map_commands() -> None:
    capabilities = get_device_info().capabilities

    assert type(capabilities.availability.get[0]) is GetBattery
    assert capabilities.availability.get[0]._is_available_check is True
    assert type(capabilities.battery.get[0]) is GetBattery
    assert capabilities.charge.execute is Charge
    assert capabilities.clean.action.command is Clean
    assert capabilities.custom.set is CustomCommand
    assert type(capabilities.error.get[0]) is GetError

    assert capabilities.fan_speed is not None
    assert type(capabilities.fan_speed.get[0]) is GetFanSpeed
    assert capabilities.fan_speed.set is SetFanSpeed
    assert capabilities.fan_speed.types == (
        FanSpeedLevel.QUIET,
        FanSpeedLevel.NORMAL,
        FanSpeedLevel.MAX,
        FanSpeedLevel.MAX_PLUS,
    )

    assert type(capabilities.life_span.get[0]) is GetLifeSpan
    assert capabilities.life_span.reset is ResetLifeSpan
    assert type(capabilities.network.get[0]) is GetNetInfo
    assert capabilities.play_sound.execute is PlaySound

    assert capabilities.settings.child_lock is not None
    assert type(capabilities.settings.child_lock.get[0]) is GetChildLock
    assert capabilities.settings.child_lock.set is SetChildLock

    assert capabilities.settings.volume is not None
    assert type(capabilities.settings.volume.get[0]) is GetVolume
    assert capabilities.settings.volume.set is SetVolume

    assert type(capabilities.state.get[0]) is GetCleanInfo
    assert type(capabilities.stats.clean.get[0]) is GetStats
    assert type(capabilities.stats.report.get[0]) is GetReportStats
    assert type(capabilities.stats.total.get[0]) is GetTotalStats


def test_eyfj07_profile_supports_expected_non_map_events() -> None:
    capabilities = get_device_info().capabilities

    expected_events = {
        AvailabilityEvent,
        BatteryEvent,
        ChildLockEvent,
        CustomCommandEvent,
        ErrorEvent,
        FanSpeedEvent,
        LifeSpanEvent,
        NetworkInfoEvent,
        ReportStatsEvent,
        StateEvent,
        StatsEvent,
        TotalStatsEvent,
        VolumeEvent,
    }

    for event in expected_events:
        assert event in capabilities._events


def test_eyfj07_profile_life_span_types_are_non_map_consumables() -> None:
    capabilities = get_device_info().capabilities

    assert capabilities.life_span.types == (
        LifeSpan.BRUSH,
        LifeSpan.FILTER,
        LifeSpan.SIDE_BRUSH,
        LifeSpan.UNIT_CARE,
    )