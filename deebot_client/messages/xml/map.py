"""Map messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.events.map import MapTraceEvent
from deebot_client.message import HandlingResult
from deebot_client.messages.xml.common import XmlMessage

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class MapP(XmlMessage):
    """MapP message.

    Probably a map piece
    """

    NAME = "MapP"

    @classmethod
    def _handle_xml(cls, _event_bus: EventBus, _xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        b"<ctl td='MapP' i='1245233875' pid='27' p='XQAABAAQJwAAAABv/f//o7f/Rz5IFXI5YVG4kYRDU5g6Z4W8UflplyVyfWyHmYdt2YVgA/k3ENxVye1lEM...fqEp3pept9Re5qT0lZFDWpoFg4D51VXQopPSDLSo2ZpM/zQ4IAhvgWIKnp7zlwcd6Ekj7U2FnOTTAQeWq3DPT+MTrAVO2wL/6mmGODzk4hBtA/wjZzOujPgEA=='/>"

        This is currently ignored as we prefer to pull map pieces
        :return: A message response
        """
        return HandlingResult.success()


class Trace(XmlMessage):
    """Trace message."""

    NAME = "trace"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        Sample message:
        <ctl td='trace' trid='631369' tf='16' tt='17' tr='XQAABAAKAAAAAG0/wEAAA2cAS5AAAA=='/>

        :return: A message response
        """
        if (
            (tf := xml.attrib.get("tf"))
            and (tt := xml.attrib.get("tt"))
            and (tr := xml.attrib.get("tr"))
        ):
            event_bus.notify(MapTraceEvent(start=int(tf), total=int(tt), data=tr))
            return HandlingResult.success()
        return HandlingResult.analyse()
