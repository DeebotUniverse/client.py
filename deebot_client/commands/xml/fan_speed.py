"""FanSpeed command module."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import FanSpeedEvent, FanSpeedLevel
from deebot_client.message import HandlingResult

from .common import XmlGetCommand, XmlSetCommand

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class GetCleanSpeed(XmlGetCommand):
    """GetCleanSpeed command."""

    NAME = "GetCleanSpeed"

    @classmethod
    def handle_set_args(
        cls, event_bus: EventBus, args: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(FanSpeedEvent(FanSpeedLevel(int(args["speed"]))))
        return HandlingResult.success()

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
                event = FanSpeedEvent(FanSpeedLevel.STANDARD)
            case "strong":
                event = FanSpeedEvent(FanSpeedLevel.STRONG)

        if event:
            event_bus.notify(event)
            return HandlingResult.success()

        return HandlingResult.analyse()


class SetCleanSpeed(XmlSetCommand):
    """Set clean speed command."""

    NAME = "SetCleanSpeed"
    get_command = GetCleanSpeed
    _mqtt_params = MappingProxyType({"speed": InitParam(FanSpeedLevel)})

    def __init__(self, speed: FanSpeedLevel | str) -> None:
        if isinstance(speed, FanSpeedLevel):
            speed = speed.name.lower()
        super().__init__({"speed": speed})
