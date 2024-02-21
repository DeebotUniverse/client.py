"""Life span commands."""
from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import CommandMqttP2P, InitParam
from deebot_client.events import LifeSpan, LifeSpanEvent
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataList

from .common import ExecuteCommand, JsonCommandWithMessageHandling

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus
    from deebot_client.util import LST


class GetLifeSpan(JsonCommandWithMessageHandling, MessageBodyDataList):
    """Get life span command."""

    name = "getLifeSpan"

    def __init__(self, life_spans: LST[LifeSpan]) -> None:
        super().__init__([life_span.value for life_span in life_spans])

    @classmethod
    def _handle_body_data_list(
        cls, event_bus: EventBus, data: list[dict[str, Any]]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        for component in data:
            if (total := int(component["total"])) <= 0:
                raise ValueError("total not positive!")

            left = int(component["left"])
            percent = round((left / total) * 100, 2)
            event_bus.notify(LifeSpanEvent(LifeSpan(component["type"]), percent, left))

        return HandlingResult.success()


class ResetLifeSpan(ExecuteCommand, CommandMqttP2P):
    """Reset life span command."""

    name = "resetLifeSpan"
    _mqtt_params = MappingProxyType({"type": InitParam(LifeSpan, "life_span")})

    def __init__(self, life_span: LifeSpan) -> None:
        super().__init__({"type": life_span.value})

    def handle_mqtt_p2p(self, event_bus: EventBus, response: dict[str, Any]) -> None:
        """Handle response received over the mqtt channel "p2p"."""
        result = self.handle(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            event_bus.request_refresh(LifeSpanEvent)
