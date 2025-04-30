"""Position command module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.message import HandlingResult
from deebot_client.messages.xml import Pos
from deebot_client.rs.map import PositionType

from .common import XmlCommandWithMessageHandling

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class GetPos(XmlCommandWithMessageHandling, Pos):
    """GetPos command."""

    NAME = "GetPos"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok" or xml.attrib.get("t") != "p":
            return HandlingResult.analyse()

        return cls._parse_xml(PositionType.DEEBOT, event_bus, xml)


class GetChargerPos(XmlCommandWithMessageHandling, Pos):
    """GetChargerPos command."""

    NAME = "GetChargerPos"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok":
            return HandlingResult.analyse()

        return cls._parse_xml(PositionType.CHARGER, event_bus, xml)
