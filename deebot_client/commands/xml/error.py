"""Error commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deebot_client.const import ERROR_CODES
from deebot_client.events import ErrorEvent, StateEvent
from deebot_client.message import HandlingResult
from deebot_client.models import State

from .common import XmlCommandWithMessageHandling

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from deebot_client.event_bus import EventBus


class GetError(XmlCommandWithMessageHandling):
    """Get error command."""

    name = "GetError"

    @classmethod
    def _handle_xml(cls, event_bus: EventBus, xml: Element) -> HandlingResult:
        """Handle xml message and notify the correct event subscribers.

        :return: A message response
        """
        error_code = int(errs) if (errs := xml.attrib["errs"]) else 0

        if error_code != 0:
            event_bus.notify(StateEvent(State.ERROR))

        description = ERROR_CODES.get(error_code)
        event_bus.notify(ErrorEvent(error_code, description))
        return HandlingResult.success()
