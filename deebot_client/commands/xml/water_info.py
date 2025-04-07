"""WaterBox command module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import (
    WaterAmount,
    WaterInfoEvent,
)
from deebot_client.message import HandlingResult

from .common import XmlGetCommand

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
        event_bus.notify(
            WaterInfoEvent(
                amount=WaterAmount.HIGH, mop_attached=(str(args["on"]) != "0")
            )
        )
        return HandlingResult.success()

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if xml.attrib.get("ret") != "ok" or not (on := xml.attrib.get("on")):
            return HandlingResult.analyse()

        event_bus.notify(
            WaterInfoEvent(amount=WaterAmount.HIGH, mop_attached=on != "0")
        )
        return HandlingResult.success()
