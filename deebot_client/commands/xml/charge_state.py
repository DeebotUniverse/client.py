"""Charge State command."""
from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.events import StateEvent
from deebot_client.message import HandlingResult
from deebot_client.models import State

from .common import XmlCommandWithMessageHandling

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element
    from deebot_client.event_bus import EventBus


class GetChargeState(XmlCommandWithMessageHandling):
    """GetChargeState command."""

    name = "GetChargeState"


    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """

        status: State | None = None

        ret = ret if (ret := xml.attrib["ret"]) else ""
        if ret != "ok":
            return HandlingResult.analyse()

        if charge := xml.find("charge"):
            type_ = charge.attrib["type"].lower()
            match(type_):
                case "slotcharging" | "slot_charging" | "wirecharging":
                    status = State.DOCKED
                case "idle":
                    status = State.IDLE
                case "going":
                    status = State.RETURNING
                case _:
                    status = State.ERROR

        if status:
            event_bus.notify(StateEvent(status))
            return HandlingResult.success()

        return HandlingResult.analyse()
