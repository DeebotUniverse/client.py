"""Charge state commands."""
from typing import Any
from xml.etree import ElementTree

from ..events import StateEvent
from ..message import HandlingResult, HandlingState, MessageBodyDataDict
from ..models import VacuumState
from .common import EventBus, NoArgsCommand
from .const import CODE


class GetChargeState(NoArgsCommand, MessageBodyDataDict):
    """Get charge state command."""

    name = "getChargeState"

    xml_name = "GetChargeState"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if data.get("isCharging") == 1:
            event_bus.notify(StateEvent(VacuumState.DOCKED))
        return HandlingResult.success()

    @classmethod
    def _handle_body_data_xml(
        cls, event_bus: EventBus, xml_message: str
    ) -> HandlingResult:
        tree = ElementTree.fromstring(xml_message)

        element = tree.find("charge")

        if element is None:
            return HandlingResult(HandlingState.ERROR)

        type = element.attrib.get("type")

        status: VacuumState | None = None
        if type == "Idle":
            status = VacuumState.DOCKED
        elif type == "SlotCharging":
            status = VacuumState.DOCKED

        if status:
            event_bus.notify(StateEvent(status))
            return HandlingResult.success()

        return HandlingResult.analyse()

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any] | str) -> HandlingResult:
        if isinstance(body, str) or body.get(CODE, 0) == 0:
            # Call this also if code is not in the body
            return super()._handle_body(event_bus, body)

        status: VacuumState | None = None
        if body.get("msg", None) == "fail":
            if body["code"] == "30007":  # Already charging
                status = VacuumState.DOCKED
            elif body["code"] == "5":  # Busy with another command
                status = VacuumState.ERROR
            elif body["code"] == "3":  # Bot in stuck state, example dust bin out
                status = VacuumState.ERROR

        if status:
            event_bus.notify(StateEvent(VacuumState.DOCKED))
            return HandlingResult.success()

        return HandlingResult.analyse()
