"""WaterBox command module."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import (
    WaterAmount,
    WaterInfoEvent,
)
from deebot_client.message import HandlingResult
from deebot_client.util import get_enum

from .common import XmlGetCommand, XmlSetCommand

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class GetWaterPermeability(XmlGetCommand):
    """GetWaterPermeability command."""

    NAME = "GetWaterPermeability"

    @classmethod
    def handle_set_args(
        cls, event_bus: EventBus, args: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(WaterInfoEvent(amount=WaterAmount(int(args["v"]))))
        return HandlingResult.success()

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok" or not (value := xml.attrib.get("v")):
            return HandlingResult.analyse()

        event_bus.notify(WaterInfoEvent(amount=WaterAmount(int(value))))
        return HandlingResult.success()


class SetWaterPermeability(XmlSetCommand):
    """SetWaterPermeability command."""

    NAME = "SetWaterPermeability"
    get_command = GetWaterPermeability
    _mqtt_params = MappingProxyType(
        {
            "amount": InitParam(WaterAmount),
        }
    )

    def __init__(self, amount: WaterAmount | str) -> None:
        if isinstance(amount, str):
            amount = get_enum(WaterAmount, amount)
        super().__init__({"v": str(amount.value)})


class GetWaterBoxInfo(XmlGetCommand):
    """GetWaterBoxInfo command."""

    NAME = "GetWaterBoxInfo"

    @classmethod
    def handle_set_args(
        cls, event_bus: EventBus, args: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(WaterInfoEvent(mop_attached=(str(args["on"]) != "0")))
        return HandlingResult.success()

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok" or not (on := xml.attrib.get("on")):
            return HandlingResult.analyse()

        event_bus.notify(WaterInfoEvent(mop_attached=on != "0"))
        return HandlingResult.success()
