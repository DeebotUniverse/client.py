"""Sleep messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.message import HandlingResult
from deebot_client.messages.xml.common import XmlMessage

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class SleepStatus(XmlMessage):
    """SleepStatus message."""

    NAME = "SleepStatus"

    @classmethod
    def _handle_xml(cls, _event_bus: EventBus, _xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        b"<ctl ts='1744467249545' td='SleepStatus' st='0'/>"

        :return: A message response
        """
        return HandlingResult.analyse()
