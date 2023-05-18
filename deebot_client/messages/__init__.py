"""Messages module."""


import re

from ..logging_filter import get_logger
from ..message import Message
from .battery import OnBattery
from .stats import ReportStats

_LOGGER = get_logger(__name__)

# fmt: off
# ordered by file asc
_MESSAGES: list[type[Message]] = [
    OnBattery,

    ReportStats
]
# fmt: on

MESSAGES: dict[str, type[Message]] = {message.name: message for message in _MESSAGES}  # type: ignore[misc]


def get_message(message_name: str) -> type[Message] | None:
    """Try to find the message for the given name.

    If there exists no exact match, some conversations are performed on the name to get message object simalr to the name.
    """

    if message_type := MESSAGES.get(message_name, None):
        return message_type

    converted_name = message_name
    # T8 series and newer
    if converted_name.endswith("_V2"):
        converted_name = converted_name[:-3]

    if message_type := MESSAGES.get(message_name, None):
        return message_type

    # Handle message starting with "on","off","report" the same as "get" commands
    converted_name = re.sub(
        "^((on)|(off)|(report))",
        "get",
        message_name,
    )

    from ..commands import (  # pylint: disable=import-outside-toplevel
        COMMANDS_WITH_HANDLING,
    )

    if found_command := COMMANDS_WITH_HANDLING.get(converted_name, None):
        if issubclass(found_command, Message):
            _LOGGER.debug("Falling back to old handling way for %s", message_name)
            return found_command

        _LOGGER.debug('Command "%s" doesn\'t support message handling', converted_name)
    else:
        _LOGGER.debug('Unknown message "%s"', message_name)

    return None
