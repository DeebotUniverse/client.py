"""DEEBOT NEO 2.0 (device class eyfj07)."""

from __future__ import annotations

from deebot_client.capabilities import (
    Capabilities,
    CapabilityClean,
    CapabilityCleanAction,
    CapabilityCustomCommand,
    CapabilityEvent,
    CapabilityExecute,
    CapabilityLifeSpan,
    CapabilitySetTypes,
    CapabilitySettings,
    CapabilityStats,
    DeviceType,
)
from deebot_client.commands.json.custom import CustomCommand
from deebot_client.commands.json.life_span import ResetLifeSpan
from deebot_client.commands.json.neo2 import (
    GetCombinedStatus,
    Neo2Charge,
    Neo2Clean,
    Neo2SetFanSpeed,
)
from deebot_client.commands.json.network import GetNetInfo
from deebot_client.commands.json.play_sound import PlaySound
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.const import DataType
from deebot_client.events import (
    AvailabilityEvent,
    BatteryEvent,
    CustomCommandEvent,
    ErrorEvent,
    FanSpeedEvent,
    LifeSpan,
    LifeSpanEvent,
    NetworkInfoEvent,
    OtaEvent,
    ReportStatsEvent,
    StateEvent,
    StatsEvent,
    TotalStatsEvent,
)
from deebot_client.events.fan_speed import FanSpeedLevel
from deebot_client.models import StaticDeviceInfo


def get_device_info() -> StaticDeviceInfo:
    """Get device info for DEEBOT NEO 2.0 (eyfj07)."""
    return StaticDeviceInfo(
        DataType.JSON,
        Capabilities(
            device_type=DeviceType.VACUUM,
            availability=CapabilityEvent(
                AvailabilityEvent,
                [GetCombinedStatus(is_available_check=True)],
            ),
            battery=CapabilityEvent(BatteryEvent, [GetCombinedStatus()]),
            charge=CapabilityExecute(Neo2Charge),
            clean=CapabilityClean(
                action=CapabilityCleanAction(command=Neo2Clean),
            ),
            custom=CapabilityCustomCommand(
                event=CustomCommandEvent, get=[], set=CustomCommand
            ),
            error=CapabilityEvent(ErrorEvent, [GetCombinedStatus()]),
            fan_speed=CapabilitySetTypes(
                event=FanSpeedEvent,
                get=[GetCombinedStatus()],
                set=Neo2SetFanSpeed,
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
                get=[GetCombinedStatus()],
                reset=ResetLifeSpan,
            ),
            network=CapabilityEvent(NetworkInfoEvent, [GetNetInfo()]),
            play_sound=CapabilityExecute(PlaySound),
            settings=CapabilitySettings(
                ota=CapabilityEvent(OtaEvent, [GetCombinedStatus()]),
            ),
            state=CapabilityEvent(StateEvent, [GetCombinedStatus()]),
            stats=CapabilityStats(
                clean=CapabilityEvent(StatsEvent, [GetStats()]),
                report=CapabilityEvent(ReportStatsEvent, []),
                total=CapabilityEvent(TotalStatsEvent, [GetTotalStats()]),
            ),
            water=None,
        ),
    )
