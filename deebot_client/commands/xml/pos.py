"""Position command module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.events import Position, PositionsEvent
from deebot_client.message import HandlingResult
from deebot_client.rs.map import PositionType

from .common import XmlCommandWithMessageHandling

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class PosParser:
    """Support class for producing Pos events."""

    @classmethod
    def __parse_xml(
        cls, position_type: PositionType, event_bus: EventBus, xml: Element
    ) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers."""
        if (p := xml.attrib.get("p")) and (xml.attrib.get("valid", "1")) != "1":
            p_x, p_y = p.split(",", 2)
            p_a = xml.attrib.get("a", 0)
            position = Position(type=position_type, x=int(p_x), y=int(p_y), a=int(p_a))
            event_bus.notify(PositionsEvent(positions=[position]))
            return HandlingResult.success()

        return HandlingResult.analyse()


class GetPos(XmlCommandWithMessageHandling, PosParser):
    """GetPos command."""

    NAME = "GetPos"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok" or xml.attrib.get("t") != "p":
            return HandlingResult.analyse()

        return cls.__parse_xml(PositionType.DEEBOT, event_bus, xml)


class GetChargerPos(XmlCommandWithMessageHandling, PosParser):
    """GetChargerPos command."""

    NAME = "GetChargerPos"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok":
            return HandlingResult.analyse()

        return cls.__parse_xml(PositionType.CHARGER, event_bus, xml)
