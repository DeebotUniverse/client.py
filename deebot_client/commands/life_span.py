"""Life span commands."""
from typing import Any, Dict, List, Union

from ..events import LifeSpan, LifeSpanEvent
from ..message import HandlingResult, HandlingState
from .common import CommandWithHandling, EventBus, _ExecuteCommand


class GetLifeSpan(CommandWithHandling):
    """Get life span command."""

    name = "getLifeSpan"

    def __init__(self) -> None:
        args = [life_span.value for life_span in LifeSpan]
        super().__init__(args)

    @classmethod
    def _handle_body_data_list(cls, event_bus: EventBus, data: List) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        for component in data:
            component_type = LifeSpan(component["type"])
            left = int(component["left"])
            total = int(component["total"])

            if total <= 0:
                raise ValueError("total not positive!")

            percent = round((left / total) * 100, 2)
            event_bus.notify(LifeSpanEvent(component_type, percent))

        return HandlingResult.success()


class ResetLifeSpan(_ExecuteCommand):
    """Reset life span command."""

    name = "resetLifeSpan"

    def __init__(
        self, type: Union[str, LifeSpan]  # pylint: disable=redefined-builtin
    ) -> None:
        if isinstance(type, LifeSpan):
            type = type.value

        self._type = type
        super().__init__({"type": type})

    def handle_mqtt_p2p(self, event_bus: EventBus, response: Dict[str, Any]) -> None:
        """Handle response received over the mqtt channel "p2p"."""
        result = self.handle(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            event_bus.notify(LifeSpanEvent(LifeSpan(self._type), 100.0))
