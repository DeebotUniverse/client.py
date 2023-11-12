"""Charge commands."""
from typing import Any
from xml.etree import ElementTree

from deebot_client.event_bus import EventBus
from deebot_client.events import StateEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult
from deebot_client.models import DeviceInfo, State

from ...authentication import Authenticator
from ...command import CommandResult
from .common import ExecuteCommand

_LOGGER = get_logger(__name__)


class Charge(ExecuteCommand):
    """Charge command."""

    name = "Charge"

    xml_has_own_element = True

    @classmethod
    def _handle_body(
        cls, event_bus: EventBus, body: dict[str, Any] | str
    ) -> HandlingResult:
        """Handle message->body and notify the correct event subscribers.

        :return: A message response
        """

        tree = ElementTree.fromstring(body)
        attributes = tree.attrib.keys()

        if len(attributes) == 0:
            return HandlingResult.analyse()

        # "resp": "<ctl ret='ok'/>", == returning
        if "ret" in attributes and tree.attrib.get("ret") == "ok":
            event_bus.notify(StateEvent(State.RETURNING))
            return HandlingResult.success()

        # "<ctl ret='fail' errno='8'/>", == already charging
        is_already_charging = (
            "errno" in attributes and int(tree.attrib.get("errno")) == 8
        )
        if is_already_charging:
            # bot is already charging
            event_bus.notify(StateEvent(State.DOCKED))
            return HandlingResult.success()

        return HandlingResult.success()

    async def _execute(
        self, authenticator: Authenticator, device_info: DeviceInfo, event_bus: EventBus
    ) -> CommandResult:
        if isinstance(self._args, dict):
            self._args.update({"type": "go"})

        return await super()._execute(authenticator, device_info, event_bus)
