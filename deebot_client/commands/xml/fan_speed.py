from xml.etree.ElementTree import Element

from deebot_client.commands.xml.common import XmlCommandWithMessageHandling
from deebot_client.event_bus import EventBus
from deebot_client.events.fan_speed import FanSpeedEvent, FanSpeedLevelXml
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult

_LOGGER = get_logger(__name__)


class GetFanSpeed(XmlCommandWithMessageHandling):
    name = "GetCleanSpeed"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        # <ctl ret="ok" speed="strong" />
        # <ctl ret="ok" speed="standard" />

        speed = xml.attrib.get("speed")

        if speed is None:
            return HandlingResult.analyse()

        event_bus.notify(FanSpeedEvent(FanSpeedLevelXml(speed)))
        return HandlingResult.success()
