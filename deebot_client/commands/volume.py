"""Volume command module."""

from collections.abc import Mapping
from typing import Any

from ..events import VolumeEvent
from ..message import HandlingResult, MessageBodyDataDict
from .common import EventBus, NoArgsCommand, SetCommand


class GetVolume(NoArgsCommand, MessageBodyDataDict):
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

    def __init__(self, volume: int, **kwargs: Mapping[str, Any]) -> None:
        # removing "total" as we don't can set it (App includes it)
        kwargs.pop("total", None)
        super().__init__({"volume": volume}, **kwargs)
