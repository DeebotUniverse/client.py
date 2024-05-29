"""Json commands module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.command import Command, CommandMqttP2P

from .advanced_mode import GetAdvancedMode, SetAdvancedMode
from .battery import GetBattery
from .border_switch import GetBorderSwitch, SetBorderSwitch
from .carpet import GetCarpetAutoFanBoost, SetCarpetAutoFanBoost
from .charge import Charge
from .charge_state import GetChargeState
from .child_lock import GetChildLock, SetChildLock
from .clean import Clean, CleanArea, CleanV2, GetCleanInfo, GetCleanInfoV2
from .clean_count import GetCleanCount, SetCleanCount
from .clean_logs import GetCleanLogs
from .clean_preference import GetCleanPreference, SetCleanPreference
from .clear_map import ClearMap
from .continuous_cleaning import GetContinuousCleaning, SetContinuousCleaning
from .cross_map_border_warning import GetCrossMapBorderWarning, SetCrossMapBorderWarning
from .cut_direction import GetCutDirection, SetCutDirection
from .efficiency import GetEfficiencyMode, SetEfficiencyMode
from .error import GetError
from .fan_speed import GetFanSpeed, SetFanSpeed
from .life_span import GetLifeSpan, ResetLifeSpan
from .map import (
    GetCachedMapInfo,
    GetMajorMap,
    GetMapSet,
    GetMapSetV2,
    GetMapSubSet,
    GetMapTrace,
    GetMinorMap,
)
from .moveup_warning import GetMoveUpWarning, SetMoveUpWarning
from .multimap_state import GetMultimapState, SetMultimapState
from .network import GetNetInfo
from .ota import GetOta, SetOta
from .play_sound import PlaySound
from .pos import GetPos
from .relocation import SetRelocationState
from .safe_protect import GetSafeProtect, SetSafeProtect
from .stats import GetStats, GetTotalStats
from .sweep_mode import GetSweepMode, SetSweepMode
from .true_detect import GetTrueDetect, SetTrueDetect
from .voice_assistant_state import GetVoiceAssistantState, SetVoiceAssistantState
from .volume import GetVolume, SetVolume
from .water_info import GetWaterInfo, SetWaterInfo
from .work_mode import GetWorkMode, SetWorkMode

if TYPE_CHECKING:
    from .common import JsonCommand

__all__ = [
    "GetAdvancedMode",
    "SetAdvancedMode",
    "GetBattery",
    "GetBorderSwitch",
    "SetBorderSwitch",
    "GetCarpetAutoFanBoost",
    "SetCarpetAutoFanBoost",
    "GetCleanCount",
    "SetCleanCount",
    "GetCleanPreference",
    "SetCleanPreference",
    "ClearMap",
    "Charge",
    "GetChildLock",
    "SetChildLock",
    "GetChargeState",
    "Clean",
    "CleanV2",
    "CleanArea",
    "GetCleanInfo",
    "GetCleanInfoV2",
    "GetCleanLogs",
    "GetContinuousCleaning",
    "SetContinuousCleaning",
    "SetCutDirection",
    "GetCutDirection",
    "GetCrossMapBorderWarning",
    "SetCrossMapBorderWarning",
    "GetEfficiencyMode",
    "SetEfficiencyMode",
    "GetError",
    "GetFanSpeed",
    "SetFanSpeed",
    "GetLifeSpan",
    "ResetLifeSpan",
    "GetCachedMapInfo",
    "GetMajorMap",
    "GetMapSet",
    "GetMapSetV2",
    "GetMapSubSet",
    "GetMapTrace",
    "GetMinorMap",
    "GetMoveUpWarning",
    "SetMoveUpWarning",
    "GetMultimapState",
    "SetMultimapState",
    "GetNetInfo",
    "GetOta",
    "SetOta",
    "PlaySound",
    "GetPos",
    "SetRelocationState",
    "GetSafeProtect",
    "SetSafeProtect",
    "GetStats",
    "GetSweepMode",
    "SetSweepMode",
    "GetTotalStats",
    "GetTrueDetect",
    "SetTrueDetect",
    "GetVoiceAssistantState",
    "SetVoiceAssistantState",
    "GetVolume",
    "SetVolume",
    "GetWaterInfo",
    "SetWaterInfo",
    "GetWorkMode",
    "SetWorkMode",
]

# fmt: off
# ordered by file asc
_COMMANDS: list[type[JsonCommand]] = [
    GetAdvancedMode,
    SetAdvancedMode,

    GetBorderSwitch,
    SetBorderSwitch,

    GetBattery,

    GetCarpetAutoFanBoost,
    SetCarpetAutoFanBoost,

    GetCleanCount,
    SetCleanCount,

    GetCleanPreference,
    SetCleanPreference,

    ClearMap,

    Charge,

    GetChargeState,

    GetChildLock,
    SetChildLock,

    Clean,
    CleanV2,
    CleanArea,
    GetCleanInfo,
    GetCleanInfoV2,


    GetCleanLogs,

    GetContinuousCleaning,
    SetContinuousCleaning,

    GetCrossMapBorderWarning,
    SetCrossMapBorderWarning,

    GetEfficiencyMode,
    SetEfficiencyMode,

    GetError,

    GetFanSpeed,
    SetFanSpeed,

    GetLifeSpan,
    ResetLifeSpan,

    GetCachedMapInfo,
    GetMajorMap,
    GetMapSet,
    GetMapSetV2,
    GetMapSubSet,
    GetMapTrace,
    GetMinorMap,

    GetMoveUpWarning,
    SetMoveUpWarning,

    GetMultimapState,
    SetMultimapState,

    GetNetInfo,

    GetOta,
    SetOta,

    PlaySound,

    GetPos,

    SetRelocationState,

    GetSafeProtect,
    SetSafeProtect,

    GetSweepMode,
    SetSweepMode,

    GetStats,
    GetTotalStats,

    GetTrueDetect,
    SetTrueDetect,

    GetVoiceAssistantState,
    SetVoiceAssistantState,

    GetVolume,
    SetVolume,

    GetWaterInfo,
    SetWaterInfo,

    GetWorkMode,
    SetWorkMode
]
# fmt: on

COMMANDS: dict[str, type[Command]] = {
    cmd.name: cmd  # type: ignore[misc]
    for cmd in _COMMANDS
}

COMMANDS_WITH_MQTT_P2P_HANDLING: dict[str, type[CommandMqttP2P]] = {
    cmd_name: cmd
    for (cmd_name, cmd) in COMMANDS.items()
    if issubclass(cmd, CommandMqttP2P)
}
