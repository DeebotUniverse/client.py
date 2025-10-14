"""Messages module."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from deebot_client.const import DataType
from deebot_client.logging_filter import get_logger

from .json import MESSAGES as JSON_MESSAGES, get_legacy_message
from .xml import MESSAGES as XML_MESSAGES

if TYPE_CHECKING:
    from deebot_client.message import Message

_LOGGER = get_logger(__name__)

MESSAGES = {
    DataType.JSON: JSON_MESSAGES,
    DataType.XML: XML_MESSAGES,
}


@lru_cache(maxsize=256)
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

    if data_type == DataType.JSON and (
        found_message := get_legacy_message(message_name, converted_name)
    ):
        return found_message

    _LOGGER.debug('Unknown message "%s"', message_name)
    return None
