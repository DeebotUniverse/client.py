"""Common xml based messages."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from defusedxml import ElementTree  # type: ignore[import-untyped]

from deebot_client.message import MessageStr

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus
    from deebot_client.message import HandlingResult


class XmlMessage(MessageStr, ABC):
    """Xml message."""

    @classmethod
    def _handle_str(cls, event_bus: EventBus, message: str) -> HandlingResult:
        """Handle string message and notify the correct event subscribers.

        :return: A message response
        """
        xml = ElementTree.fromstring(message)
        return cls._handle_xml(event_bus, xml)

    @classmethod
    @abstractmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
