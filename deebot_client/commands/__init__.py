"""Commands module."""
from typing import Dict, Type

from .advanced_mode import GetAdvancedMode, SetAdvancedMode
from .battery import GetBattery
from .carpet import GetCarpetAutoFanBoost, SetCarpetAutoFanBoost
from .charge import Charge
from .charge_state import GetChargeState
from .clean import Clean, CleanArea, GetCleanInfo
from .clean_count import GetCleanCount, SetCleanCount
from .clean_logs import GetCleanLogs
from .clean_preference import GetCleanPreference, SetCleanPreference
from .common import CommandWithHandling, CommandWithMqttP2PHandling, SetCommand
from .continuous_cleaning import GetContinuousCleaning, SetContinuousCleaning
from .error import GetError
from .fan_speed import FanSpeedLevel, GetFanSpeed, SetFanSpeed
from .life_span import GetLifeSpan, ResetLifeSpan
from .map import (
    GetCachedMapInfo,
    GetMajorMap,
    GetMapSet,
    GetMapSubSet,
    GetMapTrace,
    GetMinorMap,
)
from .multimap_state import GetMultimapState, SetMultimapState
from .play_sound import PlaySound
from .pos import GetPos
from .relocation import SetRelocationState
from .stats import GetStats, GetTotalStats
from .true_detect import GetTrueDetect, SetTrueDetect
from .volume import GetVolume, SetVolume
from .water_info import GetWaterInfo, SetWaterInfo

# fmt: off
# ordered by file asc
_COMMANDS: list[type[CommandWithHandling]] = [
    GetAdvancedMode,
    SetAdvancedMode,

    GetBattery,

    GetCarpetAutoFanBoost,
    SetCarpetAutoFanBoost,

    GetCleanCount,
    SetCleanCount,

    GetCleanPreference,
    SetCleanPreference,

    Charge,

    GetChargeState,

    Clean,
    CleanArea,
    GetCleanInfo,

    GetCleanLogs,

    GetContinuousCleaning,
    SetContinuousCleaning,

    GetError,

    GetFanSpeed,
    SetFanSpeed,

    GetLifeSpan,
    ResetLifeSpan,

    GetCachedMapInfo,
    GetMajorMap,
    GetMapSet,
    GetMapSubSet,
    GetMapTrace,
    GetMinorMap,

    GetMultimapState,
    SetMultimapState,

    PlaySound,

    GetPos,

    SetRelocationState,

    GetStats,
    GetTotalStats,

    GetTrueDetect,
    SetTrueDetect,

    GetVolume,
    SetVolume,

    GetWaterInfo,
    SetWaterInfo,
]
# fmt: on

COMMANDS_WITH_HANDLING: dict[str, type[CommandWithHandling]] = {
    cmd.name: cmd for cmd in _COMMANDS
}

COMMANDS_WITH_MQTT_P2P_HANDLING: dict[str, type[CommandWithMqttP2PHandling]] = {
    cmd_name: cmd
    for (cmd_name, cmd) in COMMANDS_WITH_HANDLING.items()
    if issubclass(cmd, CommandWithMqttP2PHandling)
}
