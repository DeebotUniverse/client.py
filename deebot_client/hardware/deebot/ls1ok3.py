"""ls1ok3 Capabilities."""

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
    CapabilityStats,
    DeviceType,
)

from deebot_client.commands.xml.charge_state import GetChargeState
from deebot_client.commands.xml.error import GetError

from deebot_client.commands.xml.stats import GetCleanSum

from deebot_client.const import DataType
from deebot_client.events import (
    AvailabilityEvent,
    CustomCommandEvent,
    ErrorEvent,
    LifeSpanEvent,
    NetworkInfoEvent,
    ReportStatsEvent,
    StateEvent,
    StatsEvent,
    TotalStatsEvent,
    VolumeEvent,
    BatteryEvent,
)
from deebot_client.models import StaticDeviceInfo, CleanAction
from deebot_client.util import short_name

from . import DEVICES
from ...commands.json import SetVolume
from ...commands.json.custom import CustomCommand
from ...commands.xml.common import XmlCommand

DEVICES[short_name(__name__)] = StaticDeviceInfo(
    DataType.XML,
    Capabilities(
        availability=CapabilityEvent(AvailabilityEvent, []),
        battery=CapabilityEvent(BatteryEvent, []),
        charge=CapabilityExecute(XmlCommand),
        clean=CapabilityClean(
            action=CapabilityCleanAction(command=CleanAction),
        ),
        custom=CapabilityCustomCommand(event=CustomCommandEvent, get=[], set=CustomCommand),
        device_type=DeviceType.VACUUM,
        error=CapabilityEvent(ErrorEvent, [GetError()]),
        life_span=CapabilityLifeSpan(
            types=(),
            event=LifeSpanEvent,
            get=[],
            reset=CustomCommand,
        ),
        network=CapabilityEvent(NetworkInfoEvent, []),
        play_sound=CapabilityExecute(XmlCommand),
        settings=CapabilitySettings(
            volume=CapabilitySet(
                event=VolumeEvent,
                get=[],
                set=SetVolume,
            ),
        ),
        state=CapabilityEvent(StateEvent, [GetChargeState()]),
        stats=CapabilityStats(
            clean=CapabilityEvent(StatsEvent, [GetCleanSum()]),
            report=CapabilityEvent(ReportStatsEvent, []),
            total=CapabilityEvent(TotalStatsEvent, [GetCleanSum()]),
        ),
    ),
)
