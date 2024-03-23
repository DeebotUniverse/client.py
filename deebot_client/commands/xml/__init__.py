"""Xml commands module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.command import Command, CommandMqttP2P

from .charge_state import GetChargeState
from .error import GetError
from .pos import GetPos

if TYPE_CHECKING:
    from .common import XmlCommand

__all__ = [
    "GetChargeState",
    "GetError",
    "GetPos",
]

# fmt: off
# ordered by file asc
_COMMANDS: list[type[XmlCommand]] = [
    GetError,
]
# fmt: on

COMMANDS: dict[str, type[Command]] = {
    cmd.name: cmd  # type: ignore[misc]
    for cmd in _COMMANDS
}

COMMANDS_WITH_MQTT_P2P_HANDLING: dict[str, type[CommandMqttP2P]] = {
    cmd_name: cmd
    for (cmd_name, cmd) in COMMANDS.items()
    if issubclass(cmd, CommandMqttP2P)
}
