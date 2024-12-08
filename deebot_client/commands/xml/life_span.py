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

    name = "GetLifeSpan"

    def __init__(self, life_span: LifeSpan) -> None:
        # type for JSON commands starts with small letter, while XML types start with upper letter. Workaround:
        xml_type = life_span.value[0].upper() + life_span.value[1:]
        super().__init__({"type": xml_type})

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if (xml.attrib.get("ret") == "ok"
                and "type" in xml.attrib
                and "left" in xml.attrib
                and "total" in xml.attrib):

            component_type = xml.attrib.get("type")
            if component_type is None:
                return HandlingResult.analyse()
            # type for JSON commands starts with small letter, while XML types start with upper letter. Workaround:
            xml_type = component_type[0].lower() + component_type[1:]

            left = int(xml.attrib.get("left", 0))
            total = int(xml.attrib.get("total", 0))
            percent: float = round((left / total) * 100, 2) if total > 0 else 0.0

            event_bus.notify(LifeSpanEvent(LifeSpan(xml_type), percent, left))
            return HandlingResult.success()

        return HandlingResult.analyse()
