"""(fan) speed commands."""
from collections.abc import Mapping
from typing import Any
from xml.etree import ElementTree

from ..events import FanSpeedEvent, FanSpeedLevel
from ..events.fan_speed import FanSpeedLevelXml
from ..message import HandlingResult, MessageBodyDataDict
from .common import EventBus, NoArgsCommand, SetCommand


class GetFanSpeed(NoArgsCommand, MessageBodyDataDict):
    """Get fan speed command."""

    name = "getSpeed"

    xml_name = "GetCleanSpeed"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(FanSpeedEvent(FanSpeedLevel(int(data["speed"]))))
        return HandlingResult.success()

    @classmethod
    def _handle_body_data_xml(
        cls, event_bus: EventBus, xml_message: str
    ) -> HandlingResult:
        tree = ElementTree.fromstring(xml_message)
        if tree is None or len(tree.attrib) == 0:
            return HandlingResult.analyse()

        event_bus.notify(FanSpeedEvent(FanSpeedLevelXml(str(tree.attrib["speed"]))))
        return HandlingResult.success()


class SetFanSpeed(SetCommand):
    """Set fan speed command."""

    name = "setSpeed"

    xml_name = "SetCleanSpeed"

    get_command = GetFanSpeed

    def __init__(
        self, speed: str | int | FanSpeedLevel, **kwargs: Mapping[str, Any]
    ) -> None:
        if isinstance(speed, str):
            speed = FanSpeedLevel.get(speed)
        if isinstance(speed, FanSpeedLevel):
            speed = speed.value

        super().__init__({"speed": speed}, **kwargs)
