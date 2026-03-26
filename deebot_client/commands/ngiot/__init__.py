"""NGIOT commands module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .battery import GetBattery
from .charge import Charge
from .clean import Clean, CleanArea, GetCleanInfo
from .custom import CustomCommand
from .error import GetError
from .fan_speed import GetFanSpeed, SetFanSpeed
from .life_span import GetLifeSpan, ResetLifeSpan
from .network import GetNetInfo
from .play_sound import PlaySound
from .stats import GetReportStats, GetStats, GetTotalStats
from .map import GetCachedMapInfo, GetMajorMap, GetMapSet, GetMapTrace, GetMinorMap
from .pos import GetPos

if TYPE_CHECKING:
    from deebot_client.command import Command

__all__ = [
    "Charge",
    "Clean",
    "CleanArea",
    "CustomCommand",
    "GetBattery",
    "GetCleanInfo",
    "GetError",
    "GetFanSpeed",
    "GetLifeSpan",
    "GetNetInfo",
    "GetReportStats",
    "GetStats",
    "GetTotalStats",
    "PlaySound",
    "ResetLifeSpan",
    "SetFanSpeed",
    "GetCachedMapInfo",
    "GetMajorMap",
    "GetMapSet",
    "GetMapTrace",
    "GetMinorMap",
    "GetPos",
]

_COMMANDS: list[type[Command]] = [
    GetBattery,
    Charge,
    Clean,
    CleanArea,
    GetCleanInfo,
    CustomCommand,
    GetError,
    GetFanSpeed,
    SetFanSpeed,
    GetLifeSpan,
    ResetLifeSpan,
    GetNetInfo,
    PlaySound,
    GetReportStats,
    GetStats,
    GetTotalStats,
    GetCachedMGetCachedMapInfo,
    GetMajorMap,
    GetMapSet,
    GetMapTrace,
    GetMinorMap,
    GetPos,apInfo,
]

COMMANDS: dict[str, type[Command]] = {cmd.NAME: cmd for cmd in _COMMANDS}