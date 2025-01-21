"""Messages module."""

from __future__ import annotations

import re

from deebot_client.const import DataType
from deebot_client.logging_filter import get_logger
from deebot_client.message import Message

from .json import MESSAGES as JSON_MESSAGES

_LOGGER = get_logger(__name__)

MESSAGES = {
    DataType.JSON: JSON_MESSAGES,
}

_LEGACY_USE_GET_COMMAND = [
    "getAdvancedMode",
    "getBreakPoint",
    "getCachedMapInfo",
    "getCarpertPressure",
    "getChargeState",
    "getCleanCount",
    "getCleanInfo",
    "getCleanPreference",
    "getEfficiency",
    "getError",
    "getLifeSpan",
    "getMajorMap",
    "getMapSet",
    "getMapSubSet",
    "getMapTrace",
    "getMinorMap",
    "getMultiMapState",
    "getNetInfo",
    "getPos",
    "getSpeed",
    "getSweepMode",
    "getTotalStats",
    "getTrueDetect",
    "getVoiceAssistantState",
    "getVolume",
    "getWaterInfo",
    "getWorkMode",
]


def get_message(message_name: str, data_type: DataType) -> type[Message] | None:
    """Try to find the message for the given name.

    If there exists no exact match, some conversations are performed on the name to get message object similar to the name.
    """
    messages = MESSAGES.get(data_type)
    if messages is None:
        _LOGGER.warning("Datatype %s is not supported.", data_type)
        return None

    if message_type := messages.get(message_name, None):
        return message_type

    converted_name = message_name
    # T8 series and newer
    converted_name = converted_name.removesuffix("_V2")

    if message_type := messages.get(converted_name, None):
        return message_type

    # Handle message starting with "on","off","report" the same as "get" commands
    converted_name = re.sub(
        "^((on)|(off)|(report))",
        "get",
        converted_name,
    )

    if converted_name not in _LEGACY_USE_GET_COMMAND:
        _LOGGER.debug('Unknown message "%s"', message_name)
        return None

    from deebot_client.commands import (  # pylint: disable=import-outside-toplevel
        COMMANDS,
    )

    if found_command := COMMANDS.get(data_type, {}).get(converted_name, None):
        if issubclass(found_command, Message):
            _LOGGER.debug("Falling back to legacy way for %s", message_name)
            return found_command

        _LOGGER.debug('Command "%s" doesn\'t support message handling', converted_name)
    else:
        _LOGGER.debug('Unknown message "%s"', message_name)

    return None
