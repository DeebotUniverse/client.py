"""Volume command module."""

from typing import Any, Dict, Mapping

from ..events import VolumeEventDto
from ..message import HandlingResult
from .common import EventBus, SetCommand, _NoArgsCommand


class GetVolume(_NoArgsCommand):
    """Get volume command."""

    name = "getVolume"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: Dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """

        event_bus.notify(
            VolumeEventDto(volume=data["volume"], maximum=data.get("total", None))
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
