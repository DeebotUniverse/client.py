"""Charge state commands."""
from typing import Any, Optional

from ..events import StatusEvent
from ..message import HandlingResult
from ..models import VacuumState
from .common import EventBus, _NoArgsCommand
from .const import CODE


class GetChargeState(_NoArgsCommand):
    """Get charge state command."""

    name = "getChargeState"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if data.get("isCharging") == 1:
            event_bus.notify(StatusEvent(True, VacuumState.DOCKED))
        return HandlingResult.success()

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        if body.get(CODE, 0) == 0:
            # Call this also if code is not in the body
            return super()._handle_body(event_bus, body)

        status: Optional[VacuumState] = None
        if body.get("msg", None) == "fail":
            if body["code"] == "30007":  # Already charging
                status = VacuumState.DOCKED
            elif body["code"] == "5":  # Busy with another command
                status = VacuumState.ERROR
            elif body["code"] == "3":  # Bot in stuck state, example dust bin out
                status = VacuumState.ERROR

        if status:
            event_bus.notify(StatusEvent(True, VacuumState.DOCKED))
            return HandlingResult.success()

        return HandlingResult.analyse()
