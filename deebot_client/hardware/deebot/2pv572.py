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
    CapabilityMap,
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
    GetLifeSpan,
    GetWaterPermeability,
    PlaySound,
    SetCleanSpeed,
)
from deebot_client.commands.xml.charge_state import GetChargeState
from deebot_client.commands.xml.error import GetError
from deebot_client.commands.xml.map import GetMapM, GetMapSt
from deebot_client.commands.xml.pos import GetPos
from deebot_client.commands.xml.stats import GetCleanSum
from deebot_client.commands.xml.water_info import GetWaterBoxInfo, SetWaterPermeability
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
    RoomsEvent,
    StateEvent,
    StatsEvent,
    TotalStatsEvent,
    WaterAmount,
    WaterInfoEvent,
)
from deebot_client.events.map import (
    CachedMapInfoEvent,
    MajorMapEvent,
    MapChangedEvent,
    MapTraceEvent,
    PositionsEvent,
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
            types=(LifeSpan.BRUSH, LifeSpan.SIDE_BRUSH, LifeSpan.DUST_CASE_HEAP),
            event=LifeSpanEvent,
            get=[
                GetLifeSpan(LifeSpan.BRUSH),
                GetLifeSpan(LifeSpan.SIDE_BRUSH),
                GetLifeSpan(LifeSpan.DUST_CASE_HEAP),
            ],
            reset=CustomCommand,
        ),
        map=CapabilityMap(
            cached_info=CapabilityEvent(CachedMapInfoEvent, [GetMapSt()]),
            changed=CapabilityEvent(MapChangedEvent, []),
            major=CapabilityEvent(MajorMapEvent, [GetMapM()]),
            position=CapabilityEvent(PositionsEvent, [GetPos()]),
            rooms=CapabilityEvent(RoomsEvent, [GetMapSt()]),
            trace=CapabilityEvent(MapTraceEvent, []),
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
        water=CapabilitySetTypes(
            event=WaterInfoEvent,
            get=[GetWaterPermeability(), GetWaterBoxInfo()],
            set=SetWaterPermeability,
            types=(
                WaterAmount.LOW,
                WaterAmount.MEDIUM,
                WaterAmount.HIGH,
            ),
        ),
    ),
)
