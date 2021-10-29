"""Charge commands."""
import logging
from typing import Any, Dict

from ..events import StatusEventDto
from ..models import VacuumState
from .common import EventBus, _ExecuteCommand

_LOGGER = logging.getLogger(__name__)


class Charge(_ExecuteCommand):
    """Charge command."""

    name = "charge"

    def __init__(self) -> None:
        super().__init__({"act": "go"})

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: Dict[str, Any]) -> bool:
        """Handle message->body and notify the correct event subscribers.

        :return: True if data was valid and no error was included
        """
        success = super()._handle_body(event_bus, body)
        if success:
            event_bus.notify(StatusEventDto(True, VacuumState.RETURNING))

        return success
