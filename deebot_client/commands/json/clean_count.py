"""Clean count command module."""

from typing import Any

from deebot_client.command import InitParam
from deebot_client.event_bus import EventBus
from deebot_client.events import CleanCountEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import CommandWithMessageHandling, SetCommand


class GetCleanCount(CommandWithMessageHandling, MessageBodyDataDict):
    """Get clean count command."""

    name = "getCleanCount"

    # TODO Potentially not available on XML based models?
    xml_name = "GetCleanCount"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """

        event_bus.notify(CleanCountEvent(count=data["count"]))
        return HandlingResult.success()

    @classmethod
    def _handle_body_data_xml(
        cls, event_bus: EventBus, xml_message: str
    ) -> HandlingResult:
        raise NotImplementedError


class SetCleanCount(SetCommand):
    """Set clean count command."""

    name = "setCleanCount"
    # TODO Potentially not available on XML based models?
    xml_name = "SetCleanCount"

    get_command = GetCleanCount
    _mqtt_params = {"count": InitParam(int)}

    def __init__(self, count: int) -> None:
        super().__init__({"count": count})
