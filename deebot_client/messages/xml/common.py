"""Battery messages."""
from abc import abstractmethod
from xml.etree.ElementTree import Element

from defusedxml.ElementTree import fromstring

from deebot_client.events.event_bus import EventBus
from deebot_client.message import HandlingResult, MessageStr


class MessageXml(MessageStr):
    """Message with handling body->data->str code."""

    @classmethod
    @abstractmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle message as xml and notify the correct event subscribers.

        :return: A message response
        """

    @classmethod
    def _handle_str(cls, event_bus: EventBus, message: str) -> HandlingResult:
        """Handle message as str and notify the correct event subscribers.

        :return: A message response
        """
        return cls._handle_xml(event_bus, fromstring(message))
