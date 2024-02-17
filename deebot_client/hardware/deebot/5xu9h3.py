"""DEEBOT GOAT G1 Capabilities."""
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
    CapabilitySet,
    CapabilitySetEnable,
    CapabilitySettings,
    CapabilityStats,
)
from deebot_client.commands.json import (
    GetBorderSwitch,
    GetChildLock,
    GetCrossMapBorderWarning,
    GetMoveupWarning,
    GetSafeProtect,
    SetBorderSwitch,
    SetChildLock,
    SetCrossMapBorderWarning,
    SetMoveupWarning,
    SetSafeProtect,
)
from deebot_client.commands.json.advanced_mode import GetAdvancedMode, SetAdvancedMode
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.charge import Charge
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.clean import CleanV2, GetCleanInfoV2
from deebot_client.commands.json.clean_count import GetCleanCount, SetCleanCount
from deebot_client.commands.json.clean_logs import GetCleanLogs
from deebot_client.commands.json.custom import CustomCommand
from deebot_client.commands.json.error import GetError
from deebot_client.commands.json.life_span import GetLifeSpan, ResetLifeSpan
from deebot_client.commands.json.map import GetCachedMapInfo, GetMajorMap, GetMapTrace
from deebot_client.commands.json.multimap_state import (
    GetMultimapState,
    SetMultimapState,
)
from deebot_client.commands.json.network import GetNetInfo
from deebot_client.commands.json.play_sound import PlaySound
from deebot_client.commands.json.pos import GetPos
from deebot_client.commands.json.relocation import SetRelocationState
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.commands.json.true_detect import GetTrueDetect, SetTrueDetect
from deebot_client.commands.json.volume import GetVolume, SetVolume
from deebot_client.const import DataType
from deebot_client.events import (
    AdvancedModeEvent,
    AvailabilityEvent,
    BatteryEvent,
    BorderSwitchEvent,
    CachedMapInfoEvent,
    ChildLockEvent,
    CleanCountEvent,
    CleanLogEvent,
    CrossMapBorderWarningEvent,
    CustomCommandEvent,
    ErrorEvent,
    LifeSpan,
    LifeSpanEvent,
    MajorMapEvent,
    MapChangedEvent,
    MapTraceEvent,
    MoveupWarningEvent,
    MultimapStateEvent,
    NetworkInfoEvent,
    PositionsEvent,
    ReportStatsEvent,
    SafeProtectEvent,
    StateEvent,
    StatsEvent,
    TotalStatsEvent,
    TrueDetectEvent,
    VolumeEvent,
)
from deebot_client.models import StaticDeviceInfo
from deebot_client.util import short_name

from . import DEVICES

DEVICES[short_name(__name__)] = StaticDeviceInfo(
    DataType.JSON,
    Capabilities(
        availability=CapabilityEvent(
            AvailabilityEvent, [GetBattery(is_available_check=True)]
        ),
        battery=CapabilityEvent(BatteryEvent, [GetBattery()]),
        charge=CapabilityExecute(Charge),
        clean=CapabilityClean(
            action=CapabilityCleanAction(command=CleanV2),
            count=CapabilitySet(CleanCountEvent, [GetCleanCount()], SetCleanCount),
            log=CapabilityEvent(CleanLogEvent, [GetCleanLogs()]),
        ),
        custom=CapabilityCustomCommand(
            event=CustomCommandEvent, get=[], set=CustomCommand
        ),
        error=CapabilityEvent(ErrorEvent, [GetError()]),
        life_span=CapabilityLifeSpan(
            types=(LifeSpan.UNIT_CARE,),
            event=LifeSpanEvent,
            get=[
                GetLifeSpan(
                    [
                        LifeSpan.UNIT_CARE,
                    ]
                )
            ],
            reset=ResetLifeSpan,
        ),
        map=CapabilityMap(
            chached_info=CapabilityEvent(CachedMapInfoEvent, [GetCachedMapInfo()]),
            changed=CapabilityEvent(MapChangedEvent, []),
            major=CapabilityEvent(MajorMapEvent, [GetMajorMap()]),
            multi_state=CapabilitySetEnable(
                MultimapStateEvent, [GetMultimapState()], SetMultimapState
            ),
            position=CapabilityEvent(PositionsEvent, [GetPos()]),
            relocation=CapabilityExecute(SetRelocationState),
            trace=CapabilityEvent(MapTraceEvent, [GetMapTrace()]),
        ),
        network=CapabilityEvent(NetworkInfoEvent, [GetNetInfo()]),
        play_sound=CapabilityExecute(PlaySound),
        settings=CapabilitySettings(
            advanced_mode=CapabilitySetEnable(
                AdvancedModeEvent, [GetAdvancedMode()], SetAdvancedMode
            ),
            border_switch=CapabilitySetEnable(
                BorderSwitchEvent, [GetBorderSwitch()], SetBorderSwitch
            ),
            child_lock=CapabilitySetEnable(
                ChildLockEvent, [GetChildLock()], SetChildLock
            ),
            moveup_warning=CapabilitySetEnable(
                MoveupWarningEvent, [GetMoveupWarning()], SetMoveupWarning
            ),
            cross_map_border_warning=CapabilitySetEnable(
                CrossMapBorderWarningEvent,
                [GetCrossMapBorderWarning()],
                SetCrossMapBorderWarning,
            ),
            safe_protect=CapabilitySetEnable(
                SafeProtectEvent, [GetSafeProtect()], SetSafeProtect
            ),
            true_detect=CapabilitySetEnable(
                TrueDetectEvent, [GetTrueDetect()], SetTrueDetect
            ),
            volume=CapabilitySet(VolumeEvent, [GetVolume()], SetVolume),
        ),
        state=CapabilityEvent(StateEvent, [GetChargeState(), GetCleanInfoV2()]),
        stats=CapabilityStats(
            clean=CapabilityEvent(StatsEvent, [GetStats()]),
            report=CapabilityEvent(ReportStatsEvent, []),
            total=CapabilityEvent(TotalStatsEvent, [GetTotalStats()]),
        ),
    ),
)
