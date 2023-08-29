"""Commands module."""
from deebot_client.command import Command, CommandMqttP2P
from deebot_client.const import DataType

from .json import COMMANDS as JSON_COMMANDS
from .json import (
    COMMANDS_WITH_MQTT_P2P_HANDLING as JSON_COMMANDS_WITH_MQTT_P2P_HANDLING,
)

COMMANDS: dict[DataType, dict[str, type[Command]]] = {DataType.JSON: JSON_COMMANDS}

COMMANDS_WITH_MQTT_P2P_HANDLING: dict[DataType, dict[str, type[CommandMqttP2P]]] = {
    DataType.JSON: JSON_COMMANDS_WITH_MQTT_P2P_HANDLING
}
