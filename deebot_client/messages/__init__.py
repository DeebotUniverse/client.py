"""Messages module."""


from ..message import Message
from ..messages.stats import ReportStats
from .battery import OnBattery

# fmt: off
# ordered by file asc
_MESSAGES: list[type[Message]] = [
    OnBattery,

    ReportStats
]
# fmt: on

MESSAGES: dict[str, type[Message]] = {message.name: message for message in _MESSAGES}  # type: ignore[misc]
