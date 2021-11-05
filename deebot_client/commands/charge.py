"""Charge commands."""
import logging
from typing import Any, Dict

from ..events import StatusEvent
from ..message import HandlingResult, HandlingState
from ..models import VacuumState
from .common import EventBus, _ExecuteCommand

_LOGGER = logging.getLogger(__name__)


class Charge(_ExecuteCommand):
    """Charge command."""

    name = "charge"

    def __init__(self) -> None:
        super().__init__({"act": "go"})

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: Dict[str, Any]) -> HandlingResult:
        """Handle message->body and notify the correct event subscribers.

        :return: A message response
        """
        response = super()._handle_body(event_bus, body)
        if response.state == HandlingState.SUCCESS:
            event_bus.notify(StatusEvent(True, VacuumState.RETURNING))

        return response
