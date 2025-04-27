"""Clean commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.events import FanSpeedEvent, FanSpeedLevel, StateEvent
from deebot_client.message import HandlingResult
from deebot_client.models import CleanAction, CleanMode, State

from .common import ExecuteCommand, XmlCommandWithMessageHandling

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class Clean(ExecuteCommand):
    """Generic start/pause/stop cleaning command."""

    NAME = "Clean"
    HAS_SUB_ELEMENT = True

    def __init__(
        self, action: CleanAction, speed: FanSpeedLevel = FanSpeedLevel.NORMAL
    ) -> None:
        super().__init__(
            {
                "type": CleanMode.AUTO.xml_value,
                "act": action.xml_value,
                "speed": speed.xml_value,
            }
        )


class CleanArea(ExecuteCommand):
    """Clean area command."""

    NAME = "Clean"
    HAS_SUB_ELEMENT = True

    def __init__(
        self,
        mode: CleanMode,
        area: str,
        cleanings: int = 1,
        speed: FanSpeedLevel = FanSpeedLevel.NORMAL,
    ) -> None:
        super().__init__(
            {
                "type": mode.xml_value,
                "act": CleanAction.START.xml_value,
                "speed": speed.xml_value,
                "deep": str(cleanings),
                "mid": area,
            }
        )


class GetCleanState(XmlCommandWithMessageHandling):
    """GetCleanState command."""

    NAME = "GetCleanState"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok" or (clean := xml.find("clean")) is None:
            return HandlingResult.analyse()

        speed_attrib = clean.attrib.get("speed")
        if speed_attrib is not None:
            fan_speed_level = FanSpeedLevel.from_xml(speed_attrib)
            event_bus.notify(FanSpeedEvent(fan_speed_level))

        clean_attrib = clean.attrib.get("st")
        if clean_attrib is not None:
            clean_action = CleanAction.from_xml(clean_attrib)
            if clean_action == CleanAction.START:
                event_bus.notify(StateEvent(State.CLEANING))
            elif clean_action == CleanAction.PAUSE:
                event_bus.notify(StateEvent(State.PAUSED))
            elif clean_action in (CleanAction.RESUME, CleanAction.STOP):
                event_bus.notify(StateEvent(State.IDLE))

        return HandlingResult.success()
