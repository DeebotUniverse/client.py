"""Xml base messages."""
from abc import ABC, abstractmethod
from typing import Any
from xml.etree.ElementTree import Element

from defusedxml import ElementTree  # type: ignore[import-untyped]

from deebot_client.event_bus import EventBus
from deebot_client.message import HandlingResult, MessageBody


class MessageBodyXml(MessageBody, ABC):
    """Xml dict message with body attribute."""

    @classmethod
    @abstractmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        """Handle message->body and notify the correct event subscribers.

        :return: A message response
        """
        xml = ElementTree.fromstring(body["resp"])
        return cls._handle_xml(event_bus, xml)
