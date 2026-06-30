"""Ecovacs GOAT A3000 LiDAR (cr0e4u) capabilities.

Device: Ecovacs GOAT A3000
Class:  cr0e4u
Type:   Lawn mower with LiDAR zone mapping

Key differences from vacuum cleaners:
- Uses ``CleanMower`` command (``clean`` endpoint with V2 content format)
  and ``CleanMowerArea`` for zone / area mowing
- Has blade and lens-brush life-span items (no main brush, filter, side-brush)
- Map data arrives via chunked ``onMI``/``onArI`` MQTT push messages
- Position pushed via ``onPos`` rather than polled via ``getPos``
- No fan speed, no water settings, no continuous cleaning mode
- Has mower-specific settings: border switch, cut direction, safe protect,
  animal protection, cut height, obstacle sensitivity, move-up warning
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
    CapabilityMap,
    CapabilitySet,
    CapabilitySetEnable,
    CapabilitySettings,
    CapabilityStats,
    DeviceType,
)
from deebot_client.commands.json.advanced_mode import GetAdvancedMode, SetAdvancedMode
from deebot_client.commands.json.battery import GetBattery
from deebot_client.commands.json.border_switch import GetBorderSwitch, SetBorderSwitch
from deebot_client.commands.json.charge import Charge
from deebot_client.commands.json.charge_state import GetChargeState
from deebot_client.commands.json.child_lock import GetChildLock, SetChildLock
from deebot_client.commands.json.clean import CleanMower, GetCleanInfo
from deebot_client.commands.json.cross_map_border_warning import (
    GetCrossMapBorderWarning,
    SetCrossMapBorderWarning,
)
from deebot_client.commands.json.custom import CustomCommand
from deebot_client.commands.json.cut_direction import GetCutDirection, SetCutDirection
from deebot_client.commands.json.error import GetError
from deebot_client.commands.json.life_span import GetLifeSpan, ResetLifeSpan
from deebot_client.commands.json.map import (
    GetMajorMap,
    GetMapSet,
    GetMapTrace,
    GetMinorMap,
    SetMajorMap,
)
from deebot_client.commands.json.moveup_warning import GetMoveUpWarning, SetMoveUpWarning
from deebot_client.commands.json.mow import CleanMowerArea, GetMI
from deebot_client.commands.json.network import GetNetInfo
from deebot_client.commands.json.play_sound import PlaySound
from deebot_client.commands.json.pos import GetPos
from deebot_client.commands.json.safe_protect import GetSafeProtect, SetSafeProtect
from deebot_client.commands.json.stats import GetStats, GetTotalStats
from deebot_client.commands.json.volume import GetVolume, SetVolume
from deebot_client.const import DataType
from deebot_client.events import (
    AdvancedModeEvent,
    AvailabilityEvent,
    BatteryEvent,
    BorderSwitchEvent,
    CachedMapInfoEvent,
    ChildLockEvent,
    CrossMapBorderWarningEvent,
    CustomCommandEvent,
    CutDirectionEvent,
    ErrorEvent,
    LifeSpan,
    LifeSpanEvent,
    MajorMapEvent,
    MapChangedEvent,
    MapTraceEvent,
    MoveUpWarningEvent,
    PositionsEvent,
    ReportStatsEvent,
    RoomsEvent,
    SafeProtectEvent,
    StateEvent,
    StatsEvent,
    TotalStatsEvent,
    VolumeEvent,
)
from deebot_client.events.network import NetworkInfoEvent
from deebot_client.models import StaticDeviceInfo


def get_device_info() -> StaticDeviceInfo:
    """Get device info for the GOAT A3000 LiDAR (cr0e4u)."""
    return StaticDeviceInfo(
        DataType.JSON,
        Capabilities(
            device_type=DeviceType.MOWER,
            availability=CapabilityEvent(
                AvailabilityEvent, [GetBattery(is_available_check=True)]
            ),
            battery=CapabilityEvent(BatteryEvent, [GetBattery()]),
            charge=CapabilityExecute(Charge),
            clean=CapabilityClean(
                action=CapabilityCleanAction(
                    command=CleanMower,
                    area=CleanMowerArea,
                ),
            ),
            custom=CapabilityCustomCommand(
                event=CustomCommandEvent, get=[], set=CustomCommand
            ),
            error=CapabilityEvent(ErrorEvent, [GetError()]),
            life_span=CapabilityLifeSpan(
                types=(LifeSpan.BLADE, LifeSpan.LENS_BRUSH),
                event=LifeSpanEvent,
                get=[GetLifeSpan([LifeSpan.BLADE, LifeSpan.LENS_BRUSH])],
                reset=ResetLifeSpan,
            ),
            # Map capability: GOAT uses a request-triggered push protocol.
            # - Zone polygons: integration sends getMI → mower streams onMI/onArI
            #   LZMA chunks → OnMI/OnArI handlers fire MapSubsetEvent.
            #   GetMI() in cached_info.get is the startup poll that triggers
            #   the initial map load (mirrors what the Ecovacs app does on connect).
            # - Trace: firmware auto-pushes onMapTrace during mowing → OnMapTrace
            #   handler (PR #1567) fires MapTraceEvent. No GET needed.
            # - Position: firmware auto-pushes onPos on each GPS fix → OnPos fires
            #   PositionsEvent. No GET needed.
            # The remaining CapabilityMap fields satisfy the dataclass contract;
            # the mower code path in image.py does not issue poll commands for them.
            map=CapabilityMap(
                cached_info=CapabilityEvent(CachedMapInfoEvent, [GetMI()]),
                changed=CapabilityEvent(MapChangedEvent, []),
                major=CapabilitySet(MajorMapEvent, [GetMajorMap()], SetMajorMap),
                minor=CapabilityExecute(GetMinorMap),
                position=CapabilityEvent(PositionsEvent, [GetPos()]),
                rooms=CapabilityEvent(RoomsEvent, []),
                set=CapabilityExecute(GetMapSet),
                # Trace: primary source is the onMapTrace push (→ MapTraceEvent).
                # GetMapTrace included as a harmless startup poll fallback.
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
                cross_map_border_warning=CapabilitySetEnable(
                    CrossMapBorderWarningEvent,
                    [GetCrossMapBorderWarning()],
                    SetCrossMapBorderWarning,
                ),
                cut_direction=CapabilitySet(
                    CutDirectionEvent, [GetCutDirection()], SetCutDirection
                ),
                moveup_warning=CapabilitySetEnable(
                    MoveUpWarningEvent, [GetMoveUpWarning()], SetMoveUpWarning
                ),
                safe_protect=CapabilitySetEnable(
                    SafeProtectEvent, [GetSafeProtect()], SetSafeProtect
                ),
                volume=CapabilitySet(VolumeEvent, [GetVolume()], SetVolume),
            ),
            state=CapabilityEvent(StateEvent, [GetChargeState(), GetCleanInfo()]),
            stats=CapabilityStats(
                clean=CapabilityEvent(StatsEvent, [GetStats()]),
                report=CapabilityEvent(ReportStatsEvent, []),
                total=CapabilityEvent(TotalStatsEvent, [GetTotalStats()]),
            ),
        ),
    )
