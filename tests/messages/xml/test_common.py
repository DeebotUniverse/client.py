from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from deebot_client.events import Event
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.messages.xml.common import XmlMessage
from tests.messages import assert_message_failure
from tests.messages.xml import assert_message

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


@dataclass(frozen=True)
class _TestEvent(Event):
    payload: str


class _TestXmlMessage(XmlMessage):
    NAME = "Test"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        if payload := xml.attrib.get("payload"):
            event_bus.notify(_TestEvent(payload))
            return HandlingResult.success()
        return HandlingResult.analyse()


async def test_XmlMessageDecoding() -> None:
    await assert_message(
        _TestXmlMessage, '<ctl ret="ok" payload="test" />', _TestEvent("test")
    )


def test_XmlMessageFailure() -> None:
    assert_message_failure(
        _TestXmlMessage, '<ctl ret="ok" />', HandlingState.ANALYSE_LOGGED
    )
