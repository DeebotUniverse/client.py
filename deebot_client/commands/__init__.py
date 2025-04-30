"""Commands module."""

from __future__ import annotations

from enum import IntEnum, unique
from typing import TYPE_CHECKING

from deebot_client.command import CommandMqttP2P
from deebot_client.const import DataType

from .json import COMMANDS as JSON_COMMANDS
from .xml import COMMANDS as XML_COMMANDS

if TYPE_CHECKING:
    from deebot_client.command import Command

COMMANDS: dict[DataType, dict[str, type[Command]]] = {
    DataType.JSON: JSON_COMMANDS,
    DataType.XML: XML_COMMANDS,
}

COMMANDS_WITH_MQTT_P2P_HANDLING: dict[DataType, dict[str, type[CommandMqttP2P]]] = {
    data_type: {
        cmd_name: cmd
        for (cmd_name, cmd) in commands.items()
        if issubclass(cmd, CommandMqttP2P)
    }
    for data_type, commands in COMMANDS.items()
}


@unique
class StationAction(IntEnum):
    """Enum class for all possible station actions."""

    EMPTY_DUSTBIN = 1
