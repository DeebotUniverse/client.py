"""Json messages."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .battery import OnBattery
from .stats import ReportStats

if TYPE_CHECKING:
    from deebot_client.message import Message

__all__ = ["OnBattery", "ReportStats"]

# fmt: off
# ordered by file asc
_MESSAGES: list[type[Message]] = [
    OnBattery,

    ReportStats
]
# fmt: on

MESSAGES: dict[str, type[Message]] = {message.name: message for message in _MESSAGES}  # type: ignore[misc]
