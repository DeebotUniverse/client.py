"""Json commands module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import auto_empty, station_action, station_state
from .advanced_mode import GetAdvancedMode, SetAdvancedMode
from .anim_protect import GetAnimProtect, SetAnimProtect
from .area_parameter import GetAreaParameter, SetAreaParameter
from .area_set import GetAreaSet
from .auto_cut_direction import GetAutoCutDirection, SetAutoCutDirection
from .battery import GetBattery
from .border_spin import GetBorderSpin, SetBorderSpin
from .border_switch import GetBorderSwitch, SetBorderSwitch
from .carpet import GetCarpetAutoFanBoost, SetCarpetAutoFanBoost
from .charge import Charge
from .charge_info import GetChargeInfo
from .charge_state import GetChargeState
from .child_lock import GetChildLock, SetChildLock
from .clean import (
    Clean,
    CleanArea,
    CleanV2,
    GetCleanInfo,
    GetCleanInfoV2,
    GetScheduleTaskInfo,
)
from .clean_count import GetCleanCount, SetCleanCount
from .clean_logs import GetCleanLogs
from .clean_preference import GetCleanPreference, SetCleanPreference
from .clear_map import ClearMap
from .continuous_cleaning import GetContinuousCleaning, SetContinuousCleaning
from .cross_map_border_warning import GetCrossMapBorderWarning, SetCrossMapBorderWarning
from .cut_direction import GetCutDirection, SetCutDirection
from .cut_efficiency import GetCutEfficiency, SetCutEfficiency
from .efficiency import GetEfficiencyMode, SetEfficiencyMode
from .error import GetError
from .fan_speed import GetFanSpeed, SetFanSpeed
from .geolocation import GetGeolocation, SetGeolocation
from .life_span import GetLifeSpan, ResetLifeSpan
from .map import (
    GetCachedMapInfo,
    GetMajorMap,
    GetMapInfoV2,
    GetMapSet,
    GetMapSetV2,
    GetMapSubSet,
    GetMapTrace,
    GetMinorMap,
    SetMajorMap,
)
from .mop_auto_wash_frequency import GetMopAutoWashFrequency, SetMopAutoWashFrequency
from .moveup_warning import GetMoveUpWarning, SetMoveUpWarning
from .multimap_state import GetMultimapState, SetMultimapState
from .network import GetNetInfo, GetNetInfoLegacy
from .ota import GetOta, SetOta
from .play_sound import PlaySound
from .pos import GetPos
from .protect_state import GetProtectState
from .rain_delay import GetRainDelay, SetRainDelay
from .recognization import GetRecognization, SetRecognization
from .relocation import SetRelocationState
from .rtk import GetRtk
from .safe_protect import GetSafeProtect, SetSafeProtect
from .schedule_task import SetScheduleTask
from .stats import GetStats, GetTotalStats
from .sweep_mode import GetSweepMode, SetSweepMode
from .true_detect import GetTrueDetect, SetTrueDetect
from .voice_assistant_state import GetVoiceAssistantState, SetVoiceAssistantState
from .volume import GetVolume, SetVolume
from .water_info import GetWaterInfo, SetWaterInfo
from .work_mode import GetWorkMode, SetWorkMode

if TYPE_CHECKING:
    from deebot_client.command import Command

    from .common import JsonCommand

__all__ = [
    "Charge",
    "Clean",
    "CleanArea",
    "CleanV2",
    "ClearMap",
    "GetAdvancedMode",
    "GetAnimProtect",
    "GetAreaParameter",
    "GetAreaSet",
    "GetAutoCutDirection",
    "GetBattery",
    "GetBorderSpin",
    "GetBorderSwitch",
    "GetCachedMapInfo",
    "GetCarpetAutoFanBoost",
    "GetChargeInfo",
    "GetChargeState",
    "GetChildLock",
    "GetCleanCount",
    "GetCleanInfo",
    "GetCleanInfoV2",
    "GetCleanLogs",
    "GetCleanPreference",
    "GetContinuousCleaning",
    "GetCrossMapBorderWarning",
    "GetCutDirection",
    "GetCutEfficiency",
    "GetEfficiencyMode",
    "GetError",
    "GetFanSpeed",
    "GetGeolocation",
    "GetLifeSpan",
    "GetMajorMap",
    "GetMapInfoV2",
    "GetMapSet",
    "GetMapSetV2",
    "GetMapSubSet",
    "GetMapTrace",
    "GetMinorMap",
    "GetMopAutoWashFrequency",
    "GetMoveUpWarning",
    "GetMultimapState",
    "GetNetInfo",
    "GetNetInfoLegacy",
    "GetOta",
    "GetPos",
    "GetProtectState",
    "GetRainDelay",
    "GetRecognization",
    "GetRtk",
    "GetSafeProtect",
    "GetScheduleTaskInfo",
    "GetStats",
    "GetSweepMode",
    "GetTotalStats",
    "GetTrueDetect",
    "GetVoiceAssistantState",
    "GetVolume",
    "GetWaterInfo",
    "GetWorkMode",
    "PlaySound",
    "ResetLifeSpan",
    "SetAdvancedMode",
    "SetAnimProtect",
    "SetAreaParameter",
    "SetAutoCutDirection",
    "SetBorderSpin",
    "SetBorderSwitch",
    "SetCarpetAutoFanBoost",
    "SetChildLock",
    "SetCleanCount",
    "SetCleanPreference",
    "SetContinuousCleaning",
    "SetCrossMapBorderWarning",
    "SetCutDirection",
    "SetCutEfficiency",
    "SetEfficiencyMode",
    "SetFanSpeed",
    "SetGeolocation",
    "SetMajorMap",
    "SetMopAutoWashFrequency",
    "SetMoveUpWarning",
    "SetMultimapState",
    "SetOta",
    "SetRainDelay",
    "SetRecognization",
    "SetRelocationState",
    "SetSafeProtect",
    "SetScheduleTask",
    "SetSweepMode",
    "SetTrueDetect",
    "SetVoiceAssistantState",
    "SetVolume",
    "SetWaterInfo",
    "SetWorkMode",
]

# fmt: off
# ordered by file asc
_COMMANDS: list[type[JsonCommand]] = [
    GetAdvancedMode,
    SetAdvancedMode,

    GetAnimProtect,
    SetAnimProtect,

    GetAreaParameter,
    SetAreaParameter,

    GetAreaSet,

    GetAutoCutDirection,
    SetAutoCutDirection,

    auto_empty.GetAutoEmpty,
    auto_empty.SetAutoEmpty,

    GetBorderSpin,
    SetBorderSpin,

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

    GetChargeInfo,

    GetChargeState,

    GetChildLock,
    SetChildLock,

    Clean,
    CleanV2,
    CleanArea,
    GetCleanInfo,
    GetCleanInfoV2,
    GetScheduleTaskInfo,


    GetCleanLogs,

    GetContinuousCleaning,
    SetContinuousCleaning,

    GetCrossMapBorderWarning,
    SetCrossMapBorderWarning,

    GetCutEfficiency,
    SetCutEfficiency,


    GetEfficiencyMode,
    SetEfficiencyMode,

    GetError,

    GetFanSpeed,
    SetFanSpeed,

    GetGeolocation,
    SetGeolocation,

    GetLifeSpan,
    ResetLifeSpan,

    GetCachedMapInfo,
    GetMajorMap,
    GetMapInfoV2,
    GetMapSet,
    GetMapSetV2,
    GetMapSubSet,
    GetMapTrace,
    GetMinorMap,
    SetMajorMap,

    GetMopAutoWashFrequency,
    SetMopAutoWashFrequency,

    GetMoveUpWarning,
    SetMoveUpWarning,

    GetMultimapState,
    SetMultimapState,

    GetNetInfo,
    GetNetInfoLegacy,

    GetOta,
    SetOta,

    PlaySound,

    GetPos,

    GetProtectState,

    GetRainDelay,
    SetRainDelay,

    GetRecognization,
    SetRecognization,

    SetRelocationState,

    GetRtk,

    GetSafeProtect,
    SetSafeProtect,

    SetScheduleTask,

    station_action.StationAction,

    station_state.GetStationState,

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

COMMANDS: dict[str, type[Command]] = {cmd.NAME: cmd for cmd in _COMMANDS}
