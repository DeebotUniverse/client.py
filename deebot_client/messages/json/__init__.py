"""Json messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .auto_empty import OnAutoEmpty
from .battery import OnBattery
from .map import OnMapSetV2
from .station_state import OnStationState
from .stats import ReportStats

if TYPE_CHECKING:
    from deebot_client.message import Message

__all__ = [
    "OnBattery",
    "OnMapSetV2",
    "ReportStats",
]

# fmt: off
# ordered by file asc
_MESSAGES: list[type[Message]] = [
    OnAutoEmpty,

    OnBattery,

    OnMapSetV2,

    OnStationState,

    ReportStats,
]
# fmt: on

MESSAGES: dict[str, type[Message]] = {message.NAME: message for message in _MESSAGES}
