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
    CapabilitySet,
    CapabilitySetEnable,
    CapabilitySettings,
    CapabilityStats,
)
from deebot_client.commands.json import (
    GetBorderSwitch,
    GetChildLock,
    GetCrossMapBorderWarning,
    GetMoveUpWarning,
    GetSafeProtect,
    SetBorderSwitch,
    SetChildLock,
    SetCrossMapBorderWarning,
    SetMoveUpWarning,
    SetSafeProtect,
)
from deebot_client.commands.json.advanced_mode import GetAdvancedMode, SetAdvancedMode
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.charge import Charge
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.clean import CleanV2, GetCleanInfoV2
from deebot_client.commands.json.custom import CustomCommand
from deebot_client.commands.json.error import GetError
from deebot_client.commands.json.life_span import GetLifeSpan, ResetLifeSpan
from deebot_client.commands.json.network import GetNetInfo
from deebot_client.commands.json.play_sound import PlaySound
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.commands.json.true_detect import GetTrueDetect, SetTrueDetect
from deebot_client.commands.json.volume import GetVolume, SetVolume
from deebot_client.const import DataType
from deebot_client.events import (
    AdvancedModeEvent,
    AvailabilityEvent,
    BatteryEvent,
    BorderSwitchEvent,
    ChildLockEvent,
    CrossMapBorderWarningEvent,
    CustomCommandEvent,
    ErrorEvent,
    LifeSpan,
    LifeSpanEvent,
    MoveUpWarningEvent,
    NetworkInfoEvent,
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
        ),
        custom=CapabilityCustomCommand(
            event=CustomCommandEvent, get=[], set=CustomCommand
        ),
        error=CapabilityEvent(ErrorEvent, [GetError()]),
        life_span=CapabilityLifeSpan(
            types=(LifeSpan.BLADE, LifeSpan.LENS_BRUSH),
            event=LifeSpanEvent,
            get=[
                GetLifeSpan(
                    [
                        LifeSpan.BLADE,
                        LifeSpan.LENS_BRUSH,
                    ]
                )
            ],
            reset=ResetLifeSpan,
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
                MoveUpWarningEvent, [GetMoveUpWarning()], SetMoveUpWarning
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
