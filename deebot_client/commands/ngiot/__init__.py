"""NGIOT command module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .battery import GetBattery
from .charge import Charge
from .clean import Clean, CleanArea, GetCleanInfo
from .common import NgiotExecuteCommand, NgiotGetCommand, NgiotRequestCommand
from .custom import CustomCommand

if TYPE_CHECKING:
    from deebot_client.command import Command

__all__ = [
    "Charge",
    "Clean",
    "CleanArea",
    "CustomCommand",
    "GetBattery",
    "GetCleanInfo",
    "NgiotExecuteCommand",
    "NgiotGetCommand",
    "NgiotRequestCommand",
]

_COMMANDS: list[type[Command]] = [
    GetBattery,
    Charge,
    Clean,
    CleanArea,
    GetCleanInfo,
    CustomCommand,
]

COMMANDS: dict[str, type[Command]] = {cmd.NAME: cmd for cmd in _COMMANDS}
