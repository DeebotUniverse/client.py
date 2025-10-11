"""Xml commands module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .battery import GetBatteryInfo
from .charge import Charge
from .charge_state import GetChargeState
from .clean import Clean, CleanArea, GetCleanState
from .clean_logs import GetCleanLogs
from .clean_speed import GetCleanSpeed, SetCleanSpeed
from .error import GetError
from .life_span import GetLifeSpan, ResetLifeSpan
from .map import GetMapM, GetMapSet, GetMapSt, GetTrM, PullM, PullMP
from .play_sound import PlaySound
from .pos import GetChargerPos, GetPos
from .stats import GetCleanSum

if TYPE_CHECKING:
    from deebot_client.command import Command

    from .common import XmlCommand

__all__ = [
    "Charge",
    "Clean",
    "CleanArea",
    "GetBatteryInfo",
    "GetChargeState",
    "GetChargerPos",
    "GetCleanLogs",
    "GetCleanSpeed",
    "GetCleanState",
    "GetCleanSum",
    "GetError",
    "GetLifeSpan",
    "GetMapM",
    "GetMapSet",
    "GetMapSt",
    "GetPos",
    "GetTrM",
    "PlaySound",
    "PullM",
    "PullMP",
    "ResetLifeSpan",
    "SetCleanSpeed",
]

# fmt: off
# ordered by file asc
_COMMANDS: list[type[XmlCommand]] = [
    GetBatteryInfo,

    GetChargeState,

    Charge,

    Clean,
    CleanArea,
    GetCleanState,

    GetCleanLogs,

    GetCleanSpeed,
    SetCleanSpeed,

    GetError,

    GetLifeSpan,
    ResetLifeSpan,

    GetMapM,
    GetMapSet,
    GetMapSt,
    GetTrM,
    PullM,
    PullMP,

    PlaySound,

    GetChargerPos,
    GetPos,

    GetCleanSum,
]
# fmt: on

COMMANDS: dict[str, type[Command]] = {cmd.NAME: cmd for cmd in _COMMANDS}
