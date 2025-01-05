"""Life span commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.events import LifeSpan, LifeSpanEvent
from deebot_client.message import HandlingResult

from .common import XmlCommandWithMessageHandling

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class GetLifeSpan(XmlCommandWithMessageHandling):
    """GetLifeSpan command."""

    NAME = "GetLifeSpan"

    def __init__(self, life_span: LifeSpan) -> None:
        super().__init__({"type": life_span.xml_value})

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if (
            xml.attrib.get("ret") != "ok"
            or (component_type := xml.attrib.get("type")) is None
            or (left_str := xml.attrib.get("left")) is None
            or (total_str := xml.attrib.get("total")) is None
        ):
            return HandlingResult.analyse()

        percent = 0.0
        left = int(left_str)
        total = int(total_str)
        if total > 0:
            percent = round((left / total) * 100, 2)

        event_bus.notify(
            LifeSpanEvent(LifeSpan.from_xml(component_type), percent, left)
        )
        return HandlingResult.success()
