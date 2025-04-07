"""2pv572 Capabilities."""

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
    CapabilitySettings,
    CapabilitySetTypes,
    CapabilityStats,
    DeviceType,
)
from deebot_client.commands.json import SetVolume
from deebot_client.commands.json.custom import CustomCommand
from deebot_client.commands.xml import (
    Charge,
    Clean,
    CleanArea,
    GetBatteryInfo,
    GetCleanLogs,
    GetCleanSpeed,
    GetCleanState,
    PlaySound,
    SetCleanSpeed,
)
from deebot_client.commands.xml.charge_state import GetChargeState
from deebot_client.commands.xml.error import GetError
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
    LifeSpanEvent,
    NetworkInfoEvent,
    ReportStatsEvent,
    StateEvent,
    StatsEvent,
    TotalStatsEvent,
    VolumeEvent,
)
from deebot_client.models import StaticDeviceInfo
from deebot_client.util import short_name

from . import DEVICES

DEVICES[short_name(__name__)] = StaticDeviceInfo(
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
            types=(),
            event=LifeSpanEvent,
            get=[],
            reset=CustomCommand,
        ),
        network=CapabilityEvent(NetworkInfoEvent, []),
        play_sound=CapabilityExecute(PlaySound),
        settings=CapabilitySettings(
            volume=CapabilitySet(
                event=VolumeEvent,
                get=[],
                set=SetVolume,
            ),
        ),
        state=CapabilityEvent(StateEvent, [GetChargeState(), GetCleanState()]),
        stats=CapabilityStats(
            clean=CapabilityEvent(StatsEvent, [GetCleanSum()]),
            report=CapabilityEvent(ReportStatsEvent, []),
            total=CapabilityEvent(TotalStatsEvent, [GetCleanSum()]),
        ),
    ),
)
