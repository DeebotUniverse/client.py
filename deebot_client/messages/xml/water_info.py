"""Water messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.events import WaterAmount, WaterInfoEvent
from deebot_client.message import HandlingResult
from deebot_client.messages.xml.common import XmlMessage

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class WaterBoxInfo(XmlMessage):
    """WaterBoxInfo message."""

    NAME = "WaterBoxInfo"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if (on := xml.attrib.get("on")) is None:
            return HandlingResult.analyse()

        event_bus.notify(
            WaterInfoEvent(amount=WaterAmount.HIGH, mop_attached=on != "0")
        )
        return HandlingResult.success()
