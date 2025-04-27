"""FanSpeed command module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.events import FanSpeedEvent, FanSpeedLevel
from deebot_client.message import HandlingResult
from deebot_client.util import get_enum

from .common import ExecuteCommand, XmlCommandWithMessageHandling

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class GetCleanSpeed(XmlCommandWithMessageHandling):
    """GetCleanSpeed command."""

    NAME = "GetCleanSpeed"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok" or not (speed := xml.attrib.get("speed")):
            return HandlingResult.analyse()

        event_bus.notify(FanSpeedEvent(FanSpeedLevel.from_xml(speed)))
        return HandlingResult.success()


class SetCleanSpeed(ExecuteCommand):
    """SetCleanSpeed command."""

    NAME = "SetCleanSpeed"

    def __init__(self, speed: FanSpeedLevel | str) -> None:
        if isinstance(speed, str):
            speed = get_enum(FanSpeedLevel, speed)
        super().__init__({"speed": speed.xml_value})
