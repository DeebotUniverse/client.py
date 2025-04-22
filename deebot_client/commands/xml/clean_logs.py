"""Clean Logs commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.command import CommandResult
from deebot_client.events import (
    CleanLogEntry,
    CleanLogEvent,
)
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult
from deebot_client.util import get_enum

from .common import XmlCommandWithMessageHandling
from .enum import XmlStopReason

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)


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
        if (
            xml.attrib.get("ret") != "ok"
            or (resp_logs := xml.findall("CleanSt")) is None
        ):
            return HandlingResult.analyse()

        if len(resp_logs) >= 0:
            logs: list[CleanLogEntry] = []
            for log in resp_logs:
                xml_stop_reason_attrib = str(log.attrib["f"])
                stop_reason = XmlStopReason.FINISHED
                try:
                    stop_reason = get_enum(XmlStopReason, xml_stop_reason_attrib)
                except Exception as e:
                    _LOGGER.error(
                        "Could not decode stop reason: %s",
                        xml_stop_reason_attrib,
                        exc_info=e,
                    )
                try:
                    logs.append(
                        CleanLogEntry(
                            timestamp=int(log.attrib["s"]),
                            image_url="",  # Missing
                            type=log.attrib["t"],
                            area=int(log.attrib["a"]),
                            stop_reason=stop_reason.to_clean_job_status(),  # To be extracted
                            duration=int(log.attrib["l"]),
                        )
                    )
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.warning("Skipping log entry: %s", log, exc_info=True)
            event_bus.notify(CleanLogEvent(logs))
            return CommandResult.success()
        return HandlingResult.analyse()
