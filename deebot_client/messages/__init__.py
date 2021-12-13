"""Messages module."""


from typing import Dict, Type

from ..commands import COMMANDS_WITH_HANDLING
from ..message import Message
from ..messages.stats import ReportStats

# fmt: off
# ordered by file asc
_MESSAGES: list[type[Message]] = [
    ReportStats
]
# fmt: on

MESSAGES: dict[str, type[Message]] = {
    message.name: message
    for message in (
        _MESSAGES
        + [cmd for cmd in COMMANDS_WITH_HANDLING.values() if issubclass(cmd, Message)]
    )
}
