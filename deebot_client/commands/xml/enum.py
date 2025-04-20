"""Enums used only by XML messages."""

from __future__ import annotations

from enum import StrEnum, unique
from typing import Self

from deebot_client.events import CleanJobStatus


@unique
class XmlStopReason(StrEnum):
    """XML Reasons why cleaning has been stopped."""

    clean_job_status: CleanJobStatus

    def __new__(cls, value: str, clean_job_status: CleanJobStatus) -> Self:
        """Create new XmlStopReason."""
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.clean_job_status = clean_job_status
        return obj

    FINISHED = "s", CleanJobStatus.FINISHED
    BATTERY_LOW = "r", CleanJobStatus.FINISHED_WITH_WARNINGS
    STOPPED_BY_APP = "a", CleanJobStatus.MANUALLY_STOPPED
    STOPPED_BY_REMOTE_CONTROL = "i", CleanJobStatus.MANUALLY_STOPPED
    STOPPED_BY_BUTTON = "b", CleanJobStatus.MANUALLY_STOPPED
    STOPPED_BY_WARNING = "w", CleanJobStatus.FINISHED_WITH_WARNINGS
    STOPPED_BY_NO_DISTURB = "f", CleanJobStatus.FINISHED_WITH_WARNINGS
    STOPPED_BY_CLEARMAP = "m", CleanJobStatus.FINISHED_WITH_WARNINGS
    STOPPED_BY_NO_PATH = "n", CleanJobStatus.FINISHED_WITH_WARNINGS
    STOPPED_BY_NOT_IN_MAP = "u", CleanJobStatus.FINISHED_WITH_WARNINGS
    STOPPED_BY_VIRTUAL_WALL = "v", CleanJobStatus.FINISHED_WITH_WARNINGS
