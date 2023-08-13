"""Charge commands."""
from typing import Any
from xml.etree import ElementTree

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

    xml_has_own_element = True

    @classmethod
    def _handle_body(
            cls, event_bus: EventBus, body: dict[str, Any] | str
    ) -> HandlingResult:
        """Handle message->body and notify the correct event subscribers.

        :return: A message response
        """

        if isinstance(body, str):
            return cls._handle_xml_response(event_bus=event_bus, body=body)

        code = int(body.get(CODE, -1))
        if code == 0:
            event_bus.notify(StateEvent(VacuumState.RETURNING))
            return HandlingResult.success()

        if code == 30007:
            # bot is already charging
            event_bus.notify(StateEvent(VacuumState.DOCKED))
            return HandlingResult.success()

        return super()._handle_body(event_bus, body)

    @classmethod
    def _handle_xml_response(self, event_bus: EventBus, body: str) -> HandlingResult:
        tree = ElementTree.fromstring(body)
        attributes = tree.attrib.keys()

        if len(attributes) == 0:
            return HandlingResult.analyse()

        # "resp": "<ctl ret='ok'/>", == returning
        if "ret" in attributes and tree.attrib.get("ret") == "ok":
            event_bus.notify(StateEvent(VacuumState.RETURNING))
            return HandlingResult.success()

        # "<ctl ret='fail' errno='8'/>", == already charging
        is_already_charging = (
                "errno" in attributes and int(tree.attrib.get("errno")) == 8
        )
        if is_already_charging:
            # bot is already charging
            event_bus.notify(StateEvent(VacuumState.DOCKED))
            return HandlingResult.success()

        return HandlingResult.success()

    async def _execute(
            self, authenticator: Authenticator, device_info: DeviceInfo, event_bus: EventBus
    ) -> CommandResult:
        if isinstance(self._args, dict) and device_info.uses_xml_protocol:
            self._args.update({"type": "go"})

        if isinstance(self._args, dict) and not device_info.uses_xml_protocol:
            self._args.update({"act": "go"})

        return await super()._execute(authenticator, device_info, event_bus)
