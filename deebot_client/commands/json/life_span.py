"""Life span commands."""
from typing import Any

from deebot_client.command import CommandMqttP2P, InitParam
from deebot_client.events import LifeSpan, LifeSpanEvent
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataList
from deebot_client.util import LST

from .common import CommandWithMessageHandling, EventBus, ExecuteCommand


class GetLifeSpan(CommandWithMessageHandling, MessageBodyDataList):
    """Get life span command."""

    name = "getLifeSpan"

    def __init__(self, life_spans: LST[LifeSpan]) -> None:
        args = [life_span.value for life_span in life_spans]
        super().__init__(args)

    @classmethod
    def _handle_body_data_list(cls, event_bus: EventBus, data: list) -> HandlingResult:
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


class ResetLifeSpan(ExecuteCommand, CommandMqttP2P):
    """Reset life span command."""

    name = "resetLifeSpan"
    _mqtt_params = {"type": InitParam(LifeSpan, "life_span")}

    def __init__(self, life_span: LifeSpan) -> None:
        super().__init__({"type": life_span.value})

    def handle_mqtt_p2p(self, event_bus: EventBus, response: dict[str, Any]) -> None:
        """Handle response received over the mqtt channel "p2p"."""
        result = self.handle(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            event_bus.request_refresh(LifeSpanEvent)
