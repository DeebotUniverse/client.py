"""Clean event module."""

from __future__ import annotations

from dataclasses import dataclass

from deebot_client.util import DisplayNameIntEnum

from .base import Event


class CleanJobStatus(DisplayNameIntEnum):
    """Enum of the different clean job status."""

    NO_STATUS = -2
    CLEANING = -1
    # below the identified stop_reason values
    FINISHED = 1
    MANUAL_STOPPED = 2, "manual stopped"
    FINISHED_WITH_WARNINGS = 3, "finished with warnings"


@dataclass(frozen=True)
class CleanLogEntry:
    """Clean log entry representation."""

    timestamp: int
    image_url: str
    type: str
    area: int
    stop_reason: CleanJobStatus
    duration: int  # in seconds


@dataclass(frozen=True)
class CleanLogEvent(Event):
    """Clean log event representation."""

    logs: list[CleanLogEntry]


@dataclass(frozen=True)
class CleanCountEvent(Event):
    """Clean count event representation."""

    count: int
