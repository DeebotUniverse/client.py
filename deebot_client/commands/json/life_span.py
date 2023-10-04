"""Life span commands."""
from typing import Any

from deebot_client.command import CommandMqttP2P
from deebot_client.events import LifeSpan, LifeSpanEvent
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataList
from deebot_client.util import LST

from .common import CommandWithMessageHandling, EventBus, ExecuteCommand

LifeSpanType = LifeSpan | str


def _get_str(_type: LifeSpanType) -> str:
    if isinstance(_type, LifeSpan):
        return _type.value

    return _type


class GetLifeSpan(CommandWithMessageHandling, MessageBodyDataList):
    """Get life span command."""

    name = "getLifeSpan"

    def __init__(self, _types: LifeSpanType | LST[LifeSpanType]) -> None:
        if isinstance(_types, LifeSpanType):  # type: ignore[misc, arg-type]
            _types = set(_types)

        args = [_get_str(life_span) for life_span in _types]
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

    def __init__(
        self, type: str | LifeSpan  # pylint: disable=redefined-builtin
    ) -> None:
        super().__init__({"type": _get_str(type)})

    def handle_mqtt_p2p(self, event_bus: EventBus, response: dict[str, Any]) -> None:
        """Handle response received over the mqtt channel "p2p"."""
        result = self.handle(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            event_bus.request_refresh(LifeSpanEvent)
