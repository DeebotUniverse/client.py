"""OZMO 500 Capabilities."""

from __future__ import annotations

from deebot_client.capabilities import (
    Capabilities,
    CapabilityClean,
    CapabilityCleanAction,
    CapabilityCustomCommand,
    CapabilityEvent,
    CapabilityExecute,
    CapabilityLifeSpan,
    CapabilitySettings,
    CapabilitySetTypes,
    CapabilityStats,
    DeviceType,
)
from deebot_client.commands.json import GetNetInfoLegacy
from deebot_client.commands.json.custom import CustomCommand
from deebot_client.commands.xml import (
    Charge,
    Clean,
    CleanArea,
    GetBatteryInfo,
    GetCleanLogs,
    GetCleanSpeed,
    GetCleanState,
    GetError,
    GetLifeSpan,
    PlaySound,
    ResetLifeSpan,
    SetCleanSpeed,
)
from deebot_client.commands.xml.charge_state import GetChargeState
from deebot_client.commands.xml.stats import GetCleanSum
from deebot_client.const import DataType
from deebot_client.events import (
    AvailabilityEvent,
    BatteryEvent,
    CleanLogEvent,
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
)
from deebot_client.models import StaticDeviceInfo


def get_device_info() -> StaticDeviceInfo:
    """Get device info for this model."""
    return StaticDeviceInfo(
        DataType.XML,
        Capabilities(
            availability=CapabilityEvent(AvailabilityEvent, []),
            battery=CapabilityEvent(BatteryEvent, [GetBatteryInfo()]),
            charge=CapabilityExecute(Charge),
            clean=CapabilityClean(
                action=CapabilityCleanAction(command=Clean, area=CleanArea),
                log=CapabilityEvent(CleanLogEvent, [GetCleanLogs()]),
            ),
            custom=CapabilityCustomCommand(
                event=CustomCommandEvent, get=[], set=CustomCommand
            ),
            device_type=DeviceType.VACUUM,
            error=CapabilityEvent(ErrorEvent, [GetError()]),
            fan_speed=CapabilitySetTypes(
                event=FanSpeedEvent,
                get=[GetCleanSpeed()],
                set=SetCleanSpeed,
                types=(
                    FanSpeedLevel.NORMAL,
                    FanSpeedLevel.MAX,
                ),
            ),
            life_span=CapabilityLifeSpan(
                types=(LifeSpan.BRUSH, LifeSpan.SIDE_BRUSH, LifeSpan.DUST_CASE_HEAP),
                event=LifeSpanEvent,
                get=[
                    GetLifeSpan(LifeSpan.BRUSH),
                    GetLifeSpan(LifeSpan.SIDE_BRUSH),
                    GetLifeSpan(LifeSpan.DUST_CASE_HEAP),
                ],
                reset=ResetLifeSpan,
            ),
            network=CapabilityEvent(NetworkInfoEvent, [GetNetInfoLegacy()]),
            play_sound=CapabilityExecute(PlaySound),
            state=CapabilityEvent(StateEvent, [GetChargeState(), GetCleanState()]),
            stats=CapabilityStats(
                clean=CapabilityEvent(StatsEvent, []),
                report=CapabilityEvent(ReportStatsEvent, []),
                total=CapabilityEvent(TotalStatsEvent, [GetCleanSum()]),
            ),
            settings=CapabilitySettings(),
        ),
    )
