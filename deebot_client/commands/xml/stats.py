"""CleanSum command module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.events import TotalStatsEvent
from deebot_client.message import HandlingResult

from .common import XmlCommandWithMessageHandling

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class GetCleanSum(XmlCommandWithMessageHandling):
    """GetCleanSum command."""

    NAME = "GetCleanSum"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok":
            return HandlingResult.analyse()

        if (
            (area := xml.attrib.get("a"))
            and (lifetime := xml.attrib.get("l"))
            and (count := xml.attrib.get("c"))
        ):
            event_bus.notify(TotalStatsEvent(int(area), int(lifetime), int(count)))
            return HandlingResult.success()

        return HandlingResult.analyse()
