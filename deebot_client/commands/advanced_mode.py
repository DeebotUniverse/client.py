"""Advanced mode command module."""

from typing import Any, Dict, Mapping, Union

from ..events import AdvancedModeEvent
from ..message import HandlingResult
from .common import EventBus, SetCommand, _NoArgsCommand


class GetAdvancedMode(_NoArgsCommand):
    """Get advanced mode command."""

    name = "getAdvancedMode"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: Dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """

        event_bus.notify(AdvancedModeEvent(bool(data["enable"])))
        return HandlingResult.success()


class SetAdvancedMode(SetCommand):
    """Set advanced mode command."""

    name = "setAdvancedMode"
    get_command = GetAdvancedMode

    def __init__(self, enable: Union[int, bool], **kwargs: Mapping[str, Any]) -> None:
        if isinstance(enable, bool):
            enable = 1 if enable else 0
        super().__init__({"enable": enable}, **kwargs)
