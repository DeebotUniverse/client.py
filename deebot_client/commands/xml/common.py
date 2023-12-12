"""Common xml based commands."""
from abc import ABC, abstractmethod
from typing import cast
from xml.etree.ElementTree import Element, SubElement

from defusedxml import ElementTree  # type: ignore[import]

from deebot_client.command import Command, CommandWithMessageHandling
from deebot_client.const import DataType
from deebot_client.event_bus import EventBus
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, MessageStr

_LOGGER = get_logger(__name__)


class XmlCommand(Command):
    """Xml command."""

    data_type: DataType = DataType.XML

    @property  # type: ignore[misc]
    @classmethod
    def has_sub_element(cls) -> bool:
        """Return True if command has inner element."""
        return False

    def _get_payload(self) -> str:
        element = ctl_element = Element("ctl")

        if len(self._args) > 0:
            if self.has_sub_element:
                element = SubElement(element, self.name.lower())

            if isinstance(self._args, dict):
                for key, value in self._args.items():
                    element.set(key, value)

        return cast(str, ElementTree.tostring(ctl_element, "unicode"))


class XmlCommandWithMessageHandling(
    XmlCommand, CommandWithMessageHandling, MessageStr, ABC
):
    """Xml command, which handle response by itself."""

    @classmethod
    @abstractmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """

    @classmethod
    def _handle_str(cls, event_bus: EventBus, message: str) -> HandlingResult:
        """Handle string message and notify the correct event subscribers.

        :return: A message response
        """
        xml = ElementTree.fromstring(message)
        return cls._handle_xml(event_bus, xml)
