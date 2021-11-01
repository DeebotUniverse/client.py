"""Volume command module."""

from typing import Any, Dict, Mapping

from ..events import VolumeEventDto
from .common import EventBus, SetCommand, _NoArgsCommand


class GetVolume(_NoArgsCommand):
    """Get volume command."""

    name = "getVolume"

    @classmethod
    def _handle_body_data_dict(cls, event_bus: EventBus, data: Dict[str, Any]) -> bool:
        """Handle message->body->data and notify the correct event subscribers.

        :return: True if data was valid and no error was included
        """

        event_bus.notify(VolumeEventDto(value=data["volume"], maximum=data["total"]))
        return True


class SetVolume(SetCommand):
    """Set volume command."""

    name = "setVolume"
    get_command = GetVolume

    def __init__(self, value: int, maximum: int, **kwargs: Mapping[str, Any]) -> None:
        if value > maximum:
            raise ValueError("value must be lower or equal to maximum!")

        super().__init__({"volume": value, "total": maximum}, [], **kwargs)
