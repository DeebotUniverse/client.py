"""Commands module."""
from typing import Dict, List, Type

from .battery import GetBattery
from .charge import Charge
from .charge_state import GetChargeState
from .clean import Clean, CleanArea, GetCleanInfo
from .clean_logs import GetCleanLogs
from .common import CommandWithHandling, SetCommand
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
from .stats import GetStats
from .volume import GetVolume, SetVolume
from .water_info import GetWaterInfo, SetWaterInfo

# fmt: off
# ordered by file asc
_COMMANDS: List[Type[CommandWithHandling]] = [
    GetBattery,

    Charge,

    GetChargeState,

    Clean,
    CleanArea,
    GetCleanInfo,

    GetCleanLogs,

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

    GetVolume,
    SetVolume,

    GetWaterInfo,
    SetWaterInfo,
]
# fmt: on

COMMANDS_WITH_HANDLING: Dict[str, Type[CommandWithHandling]] = {
    cmd.name: cmd for cmd in _COMMANDS
}

SET_COMMAND_NAMES: Dict[str, Type[SetCommand]] = {
    cmd_name: cmd
    for (cmd_name, cmd) in COMMANDS_WITH_HANDLING.items()
    if issubclass(cmd, SetCommand)
}
