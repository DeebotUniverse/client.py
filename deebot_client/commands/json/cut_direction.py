"""Cut direction command module."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import CutDirectionEvent
from deebot_client.message import HandlingResult

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetCutDirection(JsonGetCommand):
    """Get cut direction command."""

    NAME = "getCutDirection"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(CutDirectionEvent(angle=data["angle"]))
        return HandlingResult.success()


class SetCutDirection(JsonSetCommand):
    """Set cut direction command."""

    NAME = "setCutDirection"
    get_command = GetCutDirection
    _mqtt_params = MappingProxyType({"angle": InitParam(int)})

    def __init__(self, angle: int) -> None:
        super().__init__({"angle": angle})
