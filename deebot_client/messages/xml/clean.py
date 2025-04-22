"""Clean messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.events import FanSpeedEvent, FanSpeedLevel, StateEvent
from deebot_client.message import HandlingResult
from deebot_client.messages.xml.common import XmlMessage
from deebot_client.models import CleanAction, State

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class CleanSt(XmlMessage):
    """CleanSt message."""

    NAME = "CleanSt"

    @classmethod
    def _handle_xml(cls, _event_bus: EventBus, _xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        b"<ctl td='CleanSt' a='21' s='1743945874' l='1595' t='' type='auto'/>"

        :return: A message response
        """
        return HandlingResult.analyse()


class CleanReport(XmlMessage):
    """CleanReport message."""

    NAME = "CleanReport"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if (clean := xml.find("clean")) is None:
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
        return HandlingResult.success()
