"""Charge commands."""
from typing import Any

from ..authentication import Authenticator
from ..command import CommandResult
from ..events import StateEvent
from ..logging_filter import get_logger
from ..message import HandlingResult
from ..models import DeviceInfo, VacuumState
from .common import EventBus, ExecuteCommand
from .const import CODE

_LOGGER = get_logger(__name__)


class Charge(ExecuteCommand):
    """Charge command."""

    name = "charge"

    xml_name = "Charge"

    @classmethod
    def _handle_body(cls, event_bus: EventBus, body: dict[str, Any] | str) -> HandlingResult:
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

    async def _execute(
        self, authenticator: Authenticator, device_info: DeviceInfo, event_bus: EventBus
    ) -> CommandResult:
        if device_info.uses_xml_protocol:
            self._args["type"] = "go"

        if not device_info.uses_xml_protocol:
            self._args["act"] = "go"

        return await super()._execute(authenticator, device_info, event_bus)
