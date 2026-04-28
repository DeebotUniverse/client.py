"""Hardware profile for eyfj07 NGIOT devices without map support."""

from __future__ import annotations

from deebot_client.capabilities import (
    Capabilities,
    CapabilityClean,
    CapabilityCleanAction,
    CapabilityCustomCommand,
    CapabilityEvent,
    CapabilityExecute,
    CapabilityLifeSpan,
    CapabilitySet,
    CapabilitySetEnable,
    CapabilitySettings,
    CapabilitySetTypes,
    CapabilityStats,
    DeviceType,
)
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
from deebot_client.const import DataType
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
from deebot_client.models import StaticDeviceInfo


def get_device_info() -> StaticDeviceInfo:
    """Get device info for this model."""
    return StaticDeviceInfo(
        DataType.JSON,
        Capabilities(
            device_type=DeviceType.VACUUM,
            availability=CapabilityEvent(
                AvailabilityEvent,
                [GetBattery(is_available_check=True)],
            ),
            battery=CapabilityEvent(
                BatteryEvent,
                [GetBattery()],
            ),
            charge=CapabilityExecute(Charge),
            clean=CapabilityClean(
                action=CapabilityCleanAction(command=Clean),
            ),
            custom=CapabilityCustomCommand(
                event=CustomCommandEvent,
                get=[],
                set=CustomCommand,
            ),
            error=CapabilityEvent(
                ErrorEvent,
                [GetError()],
            ),
            fan_speed=CapabilitySetTypes(
                event=FanSpeedEvent,
                get=[GetFanSpeed()],
                set=SetFanSpeed,
                types=(
                    FanSpeedLevel.QUIET,
                    FanSpeedLevel.NORMAL,
                    FanSpeedLevel.MAX,
                    FanSpeedLevel.MAX_PLUS,
                ),
            ),
            life_span=CapabilityLifeSpan(
                types=(
                    LifeSpan.BRUSH,
                    LifeSpan.FILTER,
                    LifeSpan.SIDE_BRUSH,
                    LifeSpan.UNIT_CARE,
                ),
                event=LifeSpanEvent,
                get=[GetLifeSpan()],
                reset=ResetLifeSpan,
            ),
            network=CapabilityEvent(
                NetworkInfoEvent,
                [GetNetInfo()],
            ),
            play_sound=CapabilityExecute(PlaySound),
            settings=CapabilitySettings(
                child_lock=CapabilitySetEnable(
                    ChildLockEvent,
                    [GetChildLock()],
                    SetChildLock,
                ),
                volume=CapabilitySet(
                    VolumeEvent,
                    [GetVolume()],
                    SetVolume,
                ),
            ),
            state=CapabilityEvent(
                StateEvent,
                [GetCleanInfo()],
            ),
            stats=CapabilityStats(
                clean=CapabilityEvent(StatsEvent, [GetStats()]),
                report=CapabilityEvent(ReportStatsEvent, [GetReportStats()]),
                total=CapabilityEvent(TotalStatsEvent, [GetTotalStats()]),
            ),
            water=None,
        ),
    )
