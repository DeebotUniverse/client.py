"""Life span commands."""
from typing import List

from ..events import LifeSpan, LifeSpanEvent
from ..message import HandlingResult
from .common import CommandWithHandling, EventBus


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
            event_bus.notify(LifeSpanEvent(component_type, percent, left))

        return HandlingResult.success()
