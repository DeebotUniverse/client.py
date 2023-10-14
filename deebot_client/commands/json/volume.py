"""Volume command module."""

from typing import Any

from deebot_client.command import InitParam
from deebot_client.events import VolumeEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import CommandWithMessageHandling, EventBus, SetCommand


class GetVolume(CommandWithMessageHandling, MessageBodyDataDict):
    """Get volume command."""

    name = "getVolume"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """

        event_bus.notify(
            VolumeEvent(volume=data["volume"], maximum=data.get("total", None))
        )
        return HandlingResult.success()


class SetVolume(SetCommand):
    """Set volume command."""

    name = "setVolume"
    get_command = GetVolume
    _init_params = {
        "volume": InitParam("volume", int),
        "total": InitParam(
            "total", int, True
        ),  # Remove it as we don't can set it (App includes it)
    }

    def __init__(self, volume: int) -> None:
        super().__init__({"volume": volume})
