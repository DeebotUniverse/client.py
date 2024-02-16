"""Stats event module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import Event

if TYPE_CHECKING:
    from . import CleanJobStatus


@dataclass(frozen=True)
class StatsEvent(Event):
    """Stats event representation."""

    area: int | None
    time: int | None
    type: str | None


@dataclass(frozen=True)
class ReportStatsEvent(StatsEvent):
    """Report stats event representation."""

    cleaning_id: str
    status: CleanJobStatus
    content: list[int]


@dataclass(frozen=True)
class TotalStatsEvent(Event):
    """Total stats event representation."""

    area: int
    time: int
    cleanings: int
