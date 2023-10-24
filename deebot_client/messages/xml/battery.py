from xml.etree import ElementTree
from deebot_client.events import BatteryEvent, event_bus

from deebot_client.message import HandlingResult, HandlingState


class OnBattery():
    
    name = "OnBattery"

    @classmethod
    def _handle_body_data_xml(cls, event_bus: event_bus, xml: str) -> HandlingResult:
        tree = ElementTree.fromstring(xml)
        element = tree.find("battery")

        if element is None:
            return HandlingResult(HandlingState.ERROR)

        event_bus.notify(BatteryEvent(int(element.attrib.get("power"))))
        return HandlingResult.success()