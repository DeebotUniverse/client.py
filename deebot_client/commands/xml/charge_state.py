"""Charge State command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.message import HandlingResult
from deebot_client.messages.xml import ChargeState

from .common import XmlCommandWithMessageHandling

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class GetChargeState(XmlCommandWithMessageHandling, ChargeState):
    """GetChargeState command."""

    NAME = "GetChargeState"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok":
            return HandlingResult.analyse()

        return cls._parse_xml(event_bus, xml)
