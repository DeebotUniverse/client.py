"""Position command module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.events import Position, PositionsEvent, PositionType
from deebot_client.message import HandlingResult

from .common import XmlCommandWithMessageHandling

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class GetPos(XmlCommandWithMessageHandling):
    """GetPos command."""

    name = "GetPos"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok" or xml.attrib.get("t") != "p":
            return HandlingResult.analyse()

        if p := xml.attrib.get("p"):
            p_x, p_y = p.split(",", 2)
            p_a = xml.attrib.get("a", 0)
            position = Position(
                type=PositionType.DEEBOT, x=int(p_x), y=int(p_y), a=int(p_a)
            )
            event_bus.notify(PositionsEvent(positions=[position]))
            return HandlingResult.success()

        return HandlingResult.analyse()
