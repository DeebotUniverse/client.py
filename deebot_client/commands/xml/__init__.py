"""Xml commands module."""
from deebot_client.command import Command, CommandMqttP2P

from .battery import GetBattery
from .charge import Charge
from .clean_logs import GetCleanLogs
from .common import XmlCommand
from .error import GetError
from .map import (
    GetCachedMapInfo,
    GetMajorMap,
    GetMapSet,
    GetMapSubSet,
    GetMapTrace,
    GetMinorMap,
)
from .play_sound import PlaySound
from .relocation import SetRelocationState
from .stats import GetStats, GetTotalStats

__all__ = [
    "GetBattery",
    "Charge",
    "GetCleanLogs",
    "GetError",
    "GetCachedMapInfo",
    "GetMajorMap",
    "GetMapSet",
    "GetMapSubSet",
    "GetMapTrace",
    "GetMinorMap",
    "PlaySound",
    "SetRelocationState",
    "GetStats",
    "GetTotalStats",
]

# fmt: off
# ordered by file asc
_COMMANDS: list[type[XmlCommand]] = [
    GetBattery,

    Charge,

    GetCleanLogs,

    GetError,

    GetCachedMapInfo,
    GetMajorMap,
    GetMapSet,
    GetMapSubSet,
    GetMapTrace,
    GetMinorMap,

    PlaySound,

    SetRelocationState,

    GetStats,
    GetTotalStats,
]
# fmt: on

COMMANDS: dict[str, type[Command]] = {
    cmd.name: cmd
    for cmd in _COMMANDS  # type: ignore[misc]
}

COMMANDS_WITH_MQTT_P2P_HANDLING: dict[str, type[CommandMqttP2P]] = {
    cmd_name: cmd
    for (cmd_name, cmd) in COMMANDS.items()
    if issubclass(cmd, CommandMqttP2P)
}
