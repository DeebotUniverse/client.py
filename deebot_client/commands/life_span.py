"""Life span commands."""
from typing import Any

from ..authentication import Authenticator
from ..events import LifeSpan, LifeSpanEvent
from ..message import HandlingResult, HandlingState, MessageBodyDataList
from .common import (
    CommandHandlingMqttP2P,
    CommandWithMessageHandling,
    EventBus,
    ExecuteCommand,
)
from ..models import DeviceInfo


class GetLifeSpan(CommandWithMessageHandling, MessageBodyDataList):
    """Get life span command."""

    name = "getLifeSpan"

    # TODO A different approach needs to be made for this, because the MQTT + XML API
    # Doesn't accept an array of all consumables we want to get the life span from
    xml_name = "GetLifeSpan"

    def __init__(self) -> None:
        args = [life_span.value for life_span in LifeSpan]
        super().__init__(args)

    async def _execute_api_request(
        self, authenticator: Authenticator, device_info: DeviceInfo
    ) -> dict[str, Any]:
        if not device_info.uses_xml_protocol:
            return await super()._execute_api_request(authenticator, device_info)

        # Probably need to do something with iterating over all args and then
        # firing N-number of requests for all LifeSpan enum fields except for 'heap'
        # because that one doesn't exist on the MQTT + API version

        raise NotImplementedError

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


class ResetLifeSpan(ExecuteCommand, CommandHandlingMqttP2P):
    """Reset life span command."""

    name = "resetLifeSpan"

    def __init__(
        self, type: str | LifeSpan  # pylint: disable=redefined-builtin
    ) -> None:
        if isinstance(type, LifeSpan):
            type = type.value

        self._type = type
        super().__init__({"type": type})

    def handle_mqtt_p2p(self, event_bus: EventBus, response: dict[str, Any]) -> None:
        """Handle response received over the mqtt channel "p2p"."""
        result = self.handle(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            event_bus.request_refresh(LifeSpanEvent)
