"""Life span commands."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import LifeSpan, LifeSpanEvent
from deebot_client.message import HandlingResult, HandlingState

from .common import ExecuteCommand, XmlCommandMqttP2P, XmlCommandWithMessageHandling

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class GetLifeSpan(XmlCommandWithMessageHandling):
    """GetLifeSpan command."""

    NAME = "GetLifeSpan"

    def __init__(self, life_span: LifeSpan | str) -> None:
        xml_value = (
            life_span.xml_value if isinstance(life_span, LifeSpan) else life_span
        )
        super().__init__({"type": xml_value})

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


class ResetLifeSpan(ExecuteCommand, XmlCommandMqttP2P):
    """ResetLifeSpan command."""

    NAME = "ResetLifeSpan"
    _mqtt_params = MappingProxyType({"type": InitParam(LifeSpan, "life_span")})

    def __init__(self, life_span: LifeSpan | str) -> None:
        xml_value = (
            life_span.xml_value if isinstance(life_span, LifeSpan) else life_span
        )
        super().__init__({"type": xml_value})

    def _handle_mqtt_p2p(
        self, event_bus: EventBus, response: dict[str, Any] | str
    ) -> None:
        """Handle response received over the mqtt channel "p2p"."""
        result = self.handle(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            event_bus.request_refresh(LifeSpanEvent)
