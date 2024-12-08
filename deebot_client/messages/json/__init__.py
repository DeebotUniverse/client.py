"""Json messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base_station import OnStationState
from .battery import OnBattery
from .map import OnMapSetV2
from .stats import ReportStats

if TYPE_CHECKING:
    from deebot_client.message import Message

__all__ = [
    "OnBattery",
    "OnMapSetV2",
    "OnStationState",
    "ReportStats",
]

# fmt: off
# ordered by file asc
_MESSAGES: list[type[Message]] = [
    OnBattery,
    OnMapSetV2,

    ReportStats,
    OnStationState,
]
# fmt: on

MESSAGES: dict[str, type[Message]] = {message.name: message for message in _MESSAGES}  # type: ignore[misc]
