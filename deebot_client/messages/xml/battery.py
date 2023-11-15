"""Xml battery messages."""
from defusedxml import ElementTree

from deebot_client.event_bus import EventBus
from deebot_client.events import BatteryEvent
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataDict


class OnBattery(MessageBodyDataDict):
    """On battery message."""

    name = "onBattery"

    @classmethod
    def _handle_body_data_xml(cls, event_bus: EventBus, xml: str) -> HandlingResult:
        tree = ElementTree.fromstring(xml)
        element = tree.find("battery")

        if element is None:
            return HandlingResult(HandlingState.ERROR)

        event_bus.notify(BatteryEvent(int(element.attrib.get("power"))))

        return HandlingResult.success()
