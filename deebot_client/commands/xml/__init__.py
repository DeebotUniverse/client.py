"""Xml commands module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.command import Command, CommandMqttP2P

from .battery import GetBatteryInfo
from .charge import Charge
from .charge_state import GetChargeState
from .clean import Clean, CleanArea, GetCleanState
from .clean_logs import GetCleanLogs
from .error import GetError
from .fan_speed import GetCleanSpeed, SetCleanSpeed
from .life_span import GetLifeSpan
from .play_sound import PlaySound
from .pos import GetPos
from .stats import GetCleanSum
from .water_info import GetWaterBoxInfo, GetWaterPermeability

if TYPE_CHECKING:
    from .common import XmlCommand

__all__ = [
    "Charge",
    "Clean",
    "CleanArea",
    "GetBatteryInfo",
    "GetChargeState",
    "GetCleanLogs",
    "GetCleanSpeed",
    "GetCleanState",
    "GetCleanSum",
    "GetError",
    "GetLifeSpan",
    "GetPos",
    "GetWaterBoxInfo",
    "GetWaterPermeability",
    "PlaySound",
    "SetCleanSpeed",
]

# fmt: off
# ordered by file asc
_COMMANDS: list[type[XmlCommand]] = [
    Clean,
    CleanArea,
    GetBatteryInfo,
    GetError,
    GetBatteryInfo,
    GetCleanLogs,
    GetCleanSpeed,
    GetCleanState,
    GetLifeSpan,
    GetWaterBoxInfo,
    GetWaterPermeability,
    SetCleanSpeed,
    PlaySound,
]
# fmt: on

COMMANDS: dict[str, type[Command]] = {cmd.NAME: cmd for cmd in _COMMANDS}

COMMANDS_WITH_MQTT_P2P_HANDLING: dict[str, type[CommandMqttP2P]] = {
    cmd_name: cmd
    for (cmd_name, cmd) in COMMANDS.items()
    if issubclass(cmd, CommandMqttP2P)
}
