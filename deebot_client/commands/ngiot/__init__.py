"""NGIOT command module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .battery import GetBattery
from .charge import Charge
from .child_lock import GetChildLock, SetChildLock
from .clean import Clean, CleanArea, GetCleanInfo
from .common import NgiotExecuteCommand, NgiotGetCommand, NgiotRequestCommand
from .custom import CustomCommand
from .error import GetError
from .fan_speed import GetFanSpeed, SetFanSpeed
from .life_span import GetLifeSpan, ResetLifeSpan
from .network import GetNetInfo
from .play_sound import PlaySound
from .stats import GetReportStats, GetStats, GetTotalStats
from .volume import GetVolume, SetVolume

if TYPE_CHECKING:
    from deebot_client.command import Command

__all__ = [
    "Charge",
    "Clean",
    "CleanArea",
    "CustomCommand",
    "GetBattery",
    "GetChildLock",
    "GetCleanInfo",
    "GetError",
    "GetFanSpeed",
    "GetLifeSpan",
    "GetNetInfo",
    "GetReportStats",
    "GetStats",
    "GetTotalStats",
    "GetVolume",
    "NgiotExecuteCommand",
    "NgiotGetCommand",
    "NgiotRequestCommand",
    "PlaySound",
    "ResetLifeSpan",
    "SetChildLock",
    "SetFanSpeed",
    "SetVolume",
]

_COMMANDS: list[type[Command]] = [
    GetBattery,
    Charge,
    CleanArea,
    Clean,
    GetCleanInfo,
    CustomCommand,
    GetChildLock,
    SetChildLock,
    GetError,
    GetFanSpeed,
    SetFanSpeed,
    GetLifeSpan,
    ResetLifeSpan,
    GetNetInfo,
    PlaySound,
    GetStats,
    GetReportStats,
    GetTotalStats,
    GetVolume,
    SetVolume,
]

COMMANDS: dict[str, type[Command]] = {cmd.NAME: cmd for cmd in _COMMANDS}
