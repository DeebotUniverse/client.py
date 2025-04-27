"""WaterBox command module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.commands.xml.common import (
    ExecuteCommand,
    XmlCommandWithMessageHandling,
)
from deebot_client.events.water_info import (
    WaterAmount,
    WaterAmountEvent,
)
from deebot_client.message import HandlingResult
from deebot_client.messages.xml import WaterBoxInfo
from deebot_client.util import get_enum

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class GetWaterPermeability(XmlCommandWithMessageHandling):
    """GetWaterPermeability command."""

    NAME = "GetWaterPermeability"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response.
        """
        if xml.attrib.get("ret") != "ok" or not (value := xml.attrib.get("v")):
            return HandlingResult.analyse()

        if value.isdecimal() and (value_int := int(value)) >= 0:
            event_bus.notify(WaterAmountEvent(WaterAmount(value_int)))
            return HandlingResult.success()

        return HandlingResult.analyse()


class SetWaterPermeability(ExecuteCommand):
    """SetWaterPermeability command."""

    NAME = "SetWaterPermeability"

    def __init__(self, amount: WaterAmount | str) -> None:
        if isinstance(amount, str):
            amount = get_enum(WaterAmount, amount)
        super().__init__({"v": str(amount.value)})


class GetWaterBoxInfo(XmlCommandWithMessageHandling, WaterBoxInfo):
    """GetWaterBoxInfo command."""

    NAME = "GetWaterBoxInfo"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response.
        """
        if xml.attrib.get("ret") != "ok":
            return HandlingResult.analyse()

        return cls._parse_xml(event_bus, xml)
