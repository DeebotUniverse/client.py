<<<<<<< HEAD
from xml.etree import ElementTree
from deebot_client.events import BatteryEvent, event_bus

from deebot_client.message import HandlingResult, HandlingState


class OnBattery():
    
    name = "OnBattery"

    @classmethod
    def _handle_body_data_xml(cls, event_bus: event_bus, xml: str) -> HandlingResult:
=======
"""Battery messages."""

from deebot_client.event_bus import EventBus
from deebot_client.events import BatteryEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict


class OnBattery(MessageBodyDataDict):
    """On battery message."""

    name = "onBattery"

    @classmethod
    def _handle_body_data_xml(cls, event_bus: EventBus, xml: str) -> HandlingResult:
>>>>>>> 05e2323558085b071f2fb35ea67020de17f302e3
        tree = ElementTree.fromstring(xml)
        element = tree.find("battery")

        if element is None:
            return HandlingResult(HandlingState.ERROR)

        event_bus.notify(BatteryEvent(int(element.attrib.get("power"))))
<<<<<<< HEAD
        return HandlingResult.success()
=======
        return HandlingResult.success()
>>>>>>> 05e2323558085b071f2fb35ea67020de17f302e3
