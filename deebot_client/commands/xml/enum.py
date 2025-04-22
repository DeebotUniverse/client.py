"""Enums used only by XML messages."""

from __future__ import annotations

from enum import StrEnum

from deebot_client.events import CleanJobStatus


class XmlStopReason(StrEnum):
    """Reasons why cleaning has been stopped."""

    FINISHED = "s"
    BATTERY_LOW = "r"
    STOPPED_BY_APP = "a"
    STOPPED_BY_REMOTE_CONTROL = "i"
    STOPPED_BY_BUTTON = "b"
    STOPPED_BY_WARNING = "w"
    STOPPED_BY_NO_DISTURB = "f"
    STOPPED_BY_CLEARMAP = "m"
    STOPPED_BY_NO_PATH = "n"
    STOPPED_BY_NOT_IN_MAP = "u"
    STOPPED_BY_VIRTUAL_WALL = "v"

    def to_clean_job_status(self) -> CleanJobStatus:
        """Convert this value to a CleanJobStatus for compatibility proposes."""
        if self == XmlStopReason.FINISHED:
            return CleanJobStatus.FINISHED
        if self in (
            XmlStopReason.STOPPED_BY_APP,
            XmlStopReason.STOPPED_BY_REMOTE_CONTROL,
            XmlStopReason.STOPPED_BY_BUTTON,
        ):
            return CleanJobStatus.MANUALLY_STOPPED
        return CleanJobStatus.FINISHED_WITH_WARNINGS
