"""Commands module."""
from typing import Dict, List, Type

from .advanced_mode import GetAdvancedMode, SetAdvancedMode
from .battery import GetBattery
from .carpet import GetCarpetAutoFanBoost, SetCarpetAutoFanBoost
from .charge import Charge
from .charge_state import GetChargeState
from .clean import Clean, CleanArea, GetCleanInfo
from .clean_logs import GetCleanLogs
from .common import CommandWithHandling, SetCommand
from .continuous_cleaning import GetContinuousCleaning, SetContinuousCleaning
from .error import GetError
from .fan_speed import FanSpeedLevel, GetFanSpeed, SetFanSpeed
from .life_span import GetLifeSpan
from .map import (
    GetCachedMapInfo,
    GetMajorMap,
    GetMapSet,
    GetMapSubSet,
    GetMapTrace,
    GetMinorMap,
)
from .play_sound import PlaySound
from .pos import GetPos
from .relocation import SetRelocationState
from .stats import GetStats, GetTotalStats
from .volume import GetVolume, SetVolume
from .water_info import GetWaterInfo, SetWaterInfo

# fmt: off
# ordered by file asc
_COMMANDS: List[Type[CommandWithHandling]] = [
    GetAdvancedMode,
    SetAdvancedMode,

    GetBattery,

    GetCarpetAutoFanBoost,
    SetCarpetAutoFanBoost,

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

    GetCachedMapInfo,
    GetMajorMap,
    GetMapSet,
    GetMapSubSet,
    GetMapTrace,
    GetMinorMap,

    PlaySound,

    GetPos,

    SetRelocationState,

    GetStats,
    GetTotalStats,

    GetVolume,
    SetVolume,

    GetWaterInfo,
    SetWaterInfo,
]
# fmt: on

COMMANDS_WITH_HANDLING: Dict[str, Type[CommandWithHandling]] = {
    cmd.name: cmd for cmd in _COMMANDS
}
