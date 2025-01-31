"""Commands module."""

from __future__ import annotations

from enum import IntEnum, unique
from typing import TYPE_CHECKING

from deebot_client.const import DataType

from .json import (
    COMMANDS as JSON_COMMANDS,
    COMMANDS_WITH_MQTT_P2P_HANDLING as JSON_COMMANDS_WITH_MQTT_P2P_HANDLING,
)
from .xml import (
    COMMANDS_WITH_MQTT_P2P_HANDLING as XML_COMMANDS_WITH_MQTT_P2P_HANDLING,
)

if TYPE_CHECKING:
    from deebot_client.command import Command, CommandMqttP2P

COMMANDS: dict[DataType, dict[str, type[Command]]] = {DataType.JSON: JSON_COMMANDS}

COMMANDS_WITH_MQTT_P2P_HANDLING: dict[DataType, dict[str, type[CommandMqttP2P]]] = {
    DataType.JSON: JSON_COMMANDS_WITH_MQTT_P2P_HANDLING,
    DataType.XML: XML_COMMANDS_WITH_MQTT_P2P_HANDLING,
}


@unique
class StationAction(IntEnum):
    """Enum class for all possible station actions."""

    EMPTY_DUSTBIN = 1
