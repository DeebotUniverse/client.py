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
    "getBattery",
    "getBreakPoint",
    "getCachedMapInfo",
    "getCarpertPressure",
    "getChargeState",
    "getCleanCount",
    "getCleanInfo_V2",
    "getCleanInfo",
    "getCleanInfo",
    "GetCleanLogs",
    "getCleanPreference",
    "getEfficiency",
    "getError",
    "getLifeSpan",
    "getMajorMap",
    "getMapInfo_V2",
    "getMapSet_V2",
    "getMapSet",
    "getMapSubSet",
    "getMapTrace",
    "getMinorMap",
    "getMultiMapState",
    "getNetInfo",
    "getNetInfo",
    "getOta",
    "getPos",
    "getSpeed",
    "getStats",
    "getSweepMode",
    "getTotalStats",
    "getTrueDetect",
    "getVoiceAssistantState",
    "getVolume",
    "getWaterInfo",
    "getWorkMode",
]

_NOT_SUPPORTED = [
    "onEvt",
    "onRelocationState",
    "onSleep",
    "onStationState",
    "onFwBuryPoint-baseStation-connect",
    "onFwBuryPoint-baseStation-disconnect",
    "onFwBuryPoint-bd_basicinfo-evt",
    "onFwBuryPoint-bd_basicinfo",
    "onFwBuryPoint-bd_cc10",
    "onFwBuryPoint-bd_dtofstart",
    "onFwBuryPoint-bd_gyrostart",
    "onFwBuryPoint-bd_returnchargeinfo",
    "onFwBuryPoint-bd_setting",
    "onFwBuryPoint-bd_task-charge-start",
    "onFwBuryPoint-bd_task-charge-stop",
    "onFwBuryPoint-bd_task-clean-auto-pause",
    "onFwBuryPoint-bd_task-clean-auto-start",
    "onFwBuryPoint-bd_task-clean-auto-stop",
    "onFwBuryPoint-bd_task-return-normal-start",
    "onFwBuryPoint-bd_task-return-normal-stop",
    "onFwBuryPoint-cleanResultUpload-end",
    "onFwBuryPoint-cleanResultUpload-start",
    "onFwBuryPoint-bd_task-clean-auto-resume",
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
    # Handle message starting with "on","off","report" the same as "get" commands
    converted_name = re.sub(
        "^((off)|(report))",
        "get",
        converted_name,
    )

    if message_name in _NOT_SUPPORTED:
        _LOGGER.debug('Current not supported message "%s"', message_name)
        return None

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
