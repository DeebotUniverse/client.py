"""Common xml based commands."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, cast
from xml.etree.ElementTree import Element, SubElement

from defusedxml import ElementTree  # type: ignore[import-untyped]

from deebot_client.command import (
    Command,
    CommandWithMessageHandling,
    GetCommand,
    SetCommand,
)
from deebot_client.const import DataType
from deebot_client.logging_filter import get_logger
from deebot_client.message import (
    HandlingResult,
    HandlingState,
    MessageStr,
)

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)


class XmlCommand(Command, ABC):
    """Xml command."""

    DATA_TYPE = DataType.XML
    HAS_SUB_ELEMENT = False

    def _get_payload(self) -> str:
        element = ctl_element = Element("ctl")

        if len(self._args) > 0:
            if self.HAS_SUB_ELEMENT:
                element = SubElement(element, self.NAME.lower())

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


class ExecuteCommand(XmlCommandWithMessageHandling, ABC):
    """Command, which is executing something (ex. Charge)."""

    @classmethod
    def _handle_xml(cls, _: EventBus, xml: Element) -> HandlingResult:
        """Handle message->xml and notify the correct event subscribers.

        :return: A message response
        """
        # Success event looks like <ctl ret='ok'/>
        if xml.attrib.get("ret") == "ok":
            return HandlingResult.success()

        _LOGGER.warning(
            'Command "%s" was not successful. XML response: %s', cls.NAME, xml
        )
        return HandlingResult(HandlingState.FAILED)


class XmlSetCommand(ExecuteCommand, SetCommand, ABC):
    """Xml base set command.

    Command needs to be linked to the "get" command, for handling (updating) the sensors.
    """


class XmlGetCommand(XmlCommandWithMessageHandling, GetCommand, ABC):
    """Xml get command."""

    @classmethod
    @abstractmethod
    def handle_set_args(
        cls, event_bus: EventBus, args: dict[str, Any]
    ) -> HandlingResult:
        """Handle arguments of set command."""
