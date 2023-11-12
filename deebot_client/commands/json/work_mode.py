"""Work mode commands."""
from typing import Any

from deebot_client.command import InitParam
from deebot_client.event_bus import EventBus
from deebot_client.events import WorkMode, WorkModeEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import CommandWithMessageHandling, SetCommand


class GetWorkMode(CommandWithMessageHandling, MessageBodyDataDict):
    """Get work mode command."""

    name = "getWorkMode"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(WorkModeEvent(WorkMode(int(data["mode"]))))
        return HandlingResult.success()


class SetWorkMode(SetCommand):
    """Set work mode command."""

    name = "setWorkMode"
    get_command = GetWorkMode
    _mqtt_params = {"mode": InitParam(WorkMode)}

    def __init__(self, mode: WorkMode | str) -> None:
        if isinstance(mode, str):
            mode = WorkMode.get(mode)
        super().__init__({"mode": mode.value})
