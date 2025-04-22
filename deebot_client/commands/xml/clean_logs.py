"""Clean Logs commands."""

from __future__ import annotations

from enum import StrEnum, unique
from typing import TYPE_CHECKING, Self

from deebot_client.command import CommandResult
from deebot_client.events import (
    CleanJobStatus,
    CleanLogEntry,
    CleanLogEvent,
)
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult

from .common import XmlCommandWithMessageHandling

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)


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

    @classmethod
    def from_value(cls, value: str) -> XmlStopReason:
        """Fetch the right enum member given its string value."""
        for elem in cls.__members__.values():
            if elem.value == value:
                return elem
        raise ValueError(value)


class GetCleanLogs(XmlCommandWithMessageHandling):
    """GetCleanLogs command."""

    NAME = "GetCleanLogs"

    def __init__(self, count: int = 0) -> None:
        super().__init__({"count": str(count)})

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok":
            return HandlingResult.analyse()

        resp_logs = xml.findall("CleanSt")
        logs: list[CleanLogEntry] = []
        for log in resp_logs:
            xml_stop_reason_attrib = str(log.attrib["f"])
            stop_reason = XmlStopReason.FINISHED
            try:
                stop_reason = XmlStopReason.from_value(xml_stop_reason_attrib)
            except ValueError as e:
                _LOGGER.error(
                    "Could not decode stop reason: %s",
                    xml_stop_reason_attrib,
                    exc_info=e,
                )
            try:
                logs.append(
                    CleanLogEntry(
                        timestamp=int(log.attrib["s"]),
                        image_url="",  # Not available
                        type=log.attrib["t"],
                        area=int(log.attrib["a"]),
                        stop_reason=stop_reason.clean_job_status,
                        duration=int(log.attrib["l"]),
                    )
                )
            except Exception:  # pylint: disable = broad-exception-caught
                _LOGGER.warning("Skipping log entry: %s", log, exc_info=True)
        event_bus.notify(CleanLogEvent(logs))
        return CommandResult.success()
