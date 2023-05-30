"""Charge commands."""
from typing import Any

from ..events import StateEvent
from ..logging_filter import get_logger
from ..message import HandlingResult
from ..models import VacuumState
from .common import EventBus, ExecuteCommand
from .const import CODE

_LOGGER = get_logger(__name__)


class Charge(ExecuteCommand):
    """Charge command."""

    name = "charge"

    def __init__(self) -> None:
        super().__init__({"act": "go"})

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any]) -> HandlingResult:
        """Handle message->body and notify the correct event subscribers.

        :return: A message response
        """
        code = int(body.get(CODE, -1))
        if code == 0:
            event_bus.notify(StateEvent(VacuumState.RETURNING))
            return HandlingResult.success()

        if code == 30007:
            # bot is already charging
            event_bus.notify(StateEvent(VacuumState.DOCKED))
            return HandlingResult.success()

        return super()._handle_body(event_bus, body)
