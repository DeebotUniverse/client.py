"""Charge messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.events import StateEvent
from deebot_client.message import HandlingResult
from deebot_client.messages.xml.common import XmlMessage
from deebot_client.models import State

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class ChargeState(XmlMessage):
    """ChargeState message."""

    NAME = "ChargeState"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        return cls._parse_xml(event_bus, xml)

    @classmethod
    def _parse_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        if (charge := xml.find("charge")) is not None and (
            charge_type := charge.attrib["type"]
        ) is not None:
            match charge_type.lower():
                case "slotcharging" | "slot_charging" | "wirecharging":
                    status = State.DOCKED
                case "idle":
                    status = State.IDLE
                case "going":
                    status = State.RETURNING
                case _:
                    status = State.ERROR
            event_bus.notify(StateEvent(status))
            return HandlingResult.success()

        return HandlingResult.analyse()
