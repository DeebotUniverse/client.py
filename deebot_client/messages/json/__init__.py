"""Json messages."""


from deebot_client.message import Message

from .battery import OnBattery
from .stats import ReportStats

# fmt: off
# ordered by file asc
_MESSAGES: list[type[Message]] = [
    OnBattery,

    ReportStats
]
# fmt: on

MESSAGES: dict[str, type[Message]] = {message.name: message for message in _MESSAGES}  # type: ignore[misc]
