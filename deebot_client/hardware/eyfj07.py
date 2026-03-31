"""DEEBOT eyfj07 capabilities.

This profile is scoped to loading cleanly against the current ``client.py``
capability contract. Raster map support and additional write payloads can be
added later once their command surfaces are implemented.
"""

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
    CapabilitySetEnable,
    CapabilityStats,
    DeviceType,
    CapabilityMap,
)
from deebot_client.const import DataType
from deebot_client.events import (
    AvailabilityEvent,
    BatteryEvent,
    CustomCommandEvent,
    ChildLockEvent,
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
    PositionsEvent,
    RoomsEvent,
)
from deebot_client.models import StaticDeviceInfo

from deebot_client.commands.ngiot.battery import GetBattery
from deebot_client.commands.ngiot.charge import Charge
from deebot_client.commands.ngiot.clean import Clean, CleanArea, GetCleanInfo
from deebot_client.commands.ngiot.custom import CustomCommand
from deebot_client.commands.ngiot.error import GetError
from deebot_client.commands.ngiot.fan_speed import GetFanSpeed, SetFanSpeed
from deebot_client.commands.ngiot.life_span import GetLifeSpan, ResetLifeSpan
from deebot_client.commands.ngiot.network import GetNetInfo
from deebot_client.commands.ngiot.play_sound import PlaySound
from deebot_client.commands.ngiot.child_lock import GetChildLock, SetChildLock
from deebot_client.commands.ngiot.stats import GetReportStats, GetStats, GetTotalStats
from deebot_client.commands.ngiot.map import (
    GetCachedMapInfo,
    GetMajorMap,
    GetMapSet,
    GetMapTrace,
    GetMinorMap,
)
from deebot_client.events.map import (
    CachedMapInfoEvent,
    MajorMapEvent,
    MapChangedEvent,
    MapTraceEvent,
)
from deebot_client.commands.ngiot.map import (
    GetCachedMapInfo,
    GetMajorMap,
    GetMapSet,
    GetMapTrace,
    GetMinorMap,
)
from deebot_client.commands.ngiot.pos import GetPos


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
                action=CapabilityCleanAction(
                    command=Clean,
                    area=CleanArea,
                ),
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
            map=CapabilityMap(
                    cached_info=CapabilityEvent(CachedMapInfoEvent, [GetCachedMapInfo()]),
                    changed=CapabilityEvent(MapChangedEvent, []),
                    info=None,
                    major=CapabilityEvent(MajorMapEvent, [GetMajorMap()]),
                    minor=CapabilityExecute(GetMinorMap),
                    multi_state=None,
                    position=CapabilityEvent(PositionsEvent, [GetPos()])
                    rooms=CapabilityEvent(RoomsEvent, [GetCachedMapInfo()]),
                    set=CapabilityExecute(GetMapSet),
                    trace=CapabilityEvent(MapTraceEvent, [GetMapTrace()]),
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
