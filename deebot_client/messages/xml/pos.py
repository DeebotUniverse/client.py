"""Pos messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.events import Position, PositionsEvent
from deebot_client.message import HandlingResult
from deebot_client.messages.xml.common import XmlMessage
from deebot_client.rs.map import PositionType

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class Pos(XmlMessage):
    """Pos message."""

    NAME = "Pos"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        if xml.attrib.get("t") != "p":
            return HandlingResult.analyse()

        return cls._parse_xml(PositionType.DEEBOT, event_bus, xml)

    @classmethod
    def _parse_xml(
        cls, position_type: PositionType, event_bus: EventBus, xml: Element
    ) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers."""
        if (p := xml.attrib.get("p")) and (xml.attrib.get("valid", "1")) == "1":
            p_x, p_y = p.split(",", 2)
            p_a = xml.attrib.get("a", 0)
            position = Position(type=position_type, x=int(p_x), y=int(p_y), a=int(p_a))
            event_bus.notify(PositionsEvent(positions=[position]))
            return HandlingResult.success()

        return HandlingResult.analyse()
