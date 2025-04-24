"""Pos messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.commands.xml.pos import PosParser
from deebot_client.messages.xml.common import XmlMessage
from deebot_client.rs.map import PositionType

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus
    from deebot_client.message import HandlingResult


class Pos(XmlMessage, PosParser):
    """Pos message."""

    NAME = "Pos"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        return cls.__parse_xml(PositionType.DEEBOT, event_bus, xml)
