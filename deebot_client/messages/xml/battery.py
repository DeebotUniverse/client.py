"""Xml battery messages."""
from xml.etree.ElementTree import Element

from deebot_client.event_bus import EventBus
from deebot_client.events import BatteryEvent
from deebot_client.message import HandlingResult, HandlingState

from .common import MessageBodyXml


class OnBattery(MessageBodyXml):
    """On battery message."""

    name = "onBattery"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        element = xml.find("battery")

        if element is None:
            return HandlingResult(HandlingState.ERROR)

        event_bus.notify(BatteryEvent(int(element.attrib["power"])))
        return HandlingResult.success()
