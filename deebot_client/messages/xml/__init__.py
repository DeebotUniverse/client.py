"""Xml messages."""

from ...message import Message
from .battery import OnBattery

# fmt: off
# ordered by file asc
_MESSAGES: list[type[Message]] = [
    OnBattery,
]
# fmt: on

MESSAGES: dict[str, type[Message]] = {message.name: message for message in _MESSAGES}  # type: ignore[misc]
