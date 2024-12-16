"""FanSpeed command module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.events import FanSpeedEvent, FanSpeedLevel
from deebot_client.message import HandlingResult

from .common import XmlCommandWithMessageHandling

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class GetFanSpeed(XmlCommandWithMessageHandling):
    """GetFanSpeed command."""

    NAME = "GetCleanSpeed"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok" or not (speed := xml.attrib.get("speed")):
            return HandlingResult.analyse()

        event: FanSpeedEvent | None = None

        match speed.lower():
            case "standard":
                event = FanSpeedEvent(FanSpeedLevel.NORMAL)
            case "strong":
                event = FanSpeedEvent(FanSpeedLevel.MAX)

        if event:
            event_bus.notify(event)
            return HandlingResult.success()

        return HandlingResult.analyse()
