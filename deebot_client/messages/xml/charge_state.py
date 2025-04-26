"""Charge messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.commands.xml.charge_state import ChargeStateParser
from deebot_client.messages.xml.common import XmlMessage

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus
    from deebot_client.message import HandlingResult


class ChargeState(XmlMessage, ChargeStateParser):
    """ChargeState message."""

    NAME = "ChargeState"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        return cls._parse_xml(event_bus, xml)
