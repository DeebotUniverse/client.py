"""Messages module."""
from __future__ import annotations

import re

from deebot_client.const import DataType
from deebot_client.logging_filter import get_logger
from deebot_client.message import Message

from .json import MESSAGES

_LOGGER = get_logger(__name__)


def get_message(message_name: str, data_type: DataType) -> type[Message] | None:
    """Try to find the message for the given name.

    If there exists no exact match, some conversations are performed on the name to get message object similar to the name.
    """
    if (messages := {DataType.JSON: MESSAGES}.get(data_type)) is None:
        _LOGGER.warning('Datatype "%s" is not supported', data_type)
        return None

    if message_type := messages.get(message_name, None):
        _LOGGER.debug('Known message "%s"', message_name)
        return message_type

    # Handle message starting with "on", "off" and "report" the same as "get" commands
    converted_name = re.sub(
        "^((on)|(off)|(report))",
        "get",
        message_name,
    )

    from deebot_client.commands import (  # pylint: disable=import-outside-toplevel
        COMMANDS,
    )

    if found_command := COMMANDS.get(data_type, {}).get(converted_name, None):
        if issubclass(found_command, Message):
            _LOGGER.debug(
                'Falling back to legacy way for "%s" as "%s"',
                message_name,
                converted_name,
            )
            return found_command

        _LOGGER.debug('Command "%s" does not support message handling', converted_name)
    else:
        _LOGGER.debug('Unknown message "%s"/"%s"', message_name, converted_name)

    return None
