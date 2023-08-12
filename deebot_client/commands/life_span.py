"""Life span commands."""
from typing import Any
from xml.etree import ElementTree

from ..authentication import Authenticator
from ..events import LifeSpan, LifeSpanEvent
from ..message import (
    HandlingResult,
    HandlingState,
    MessageBodyDataDict,
    MessageBodyDataList,
)
from ..models import DeviceInfo
from .common import (
    CommandHandlingMqttP2P,
    CommandWithMessageHandling,
    EventBus,
    ExecuteCommand,
)


class GetLifeSpanBrush(CommandWithMessageHandling, MessageBodyDataDict):
    # As far as I know, there is no non-XML implementation for this
    name = "GetLifeSpanBrush"

    xml_name = "GetLifeSpan"

    def __init__(self) -> None:
        args = {"type": "Brush"}
        super().__init__(args)

    @classmethod
    def _handle_body_data_dict(
        self, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        raise NotImplementedError

    @classmethod
    def _handle_body_data_xml(
        cls, event_bus: EventBus, xml_message: str
    ) -> HandlingResult:
        element = ElementTree.fromstring(xml_message)

        if element.attrib.get("ret") != "ok":
            return HandlingResult.analyse()

        left = int(element.attrib.get("left"))
        total = int(element.attrib.get("total"))

        if total < 0:
            raise ValueError("total is not positive!")

        percentage = round((left / total) * 100, 2)
        event_bus.notify(LifeSpanEvent(LifeSpan.BRUSH, percentage, left))

        return HandlingResult.success()


class GetLifeSpanSideBrush(CommandWithMessageHandling, MessageBodyDataDict):
    # As far as I know, there is no non-XML implementation for this
    name = "GetLifeSpanSideBrush"

    xml_name = "GetLifeSpan"

    def __init__(self) -> None:
        args = {"type": "SideBrush"}
        super().__init__(args)

    @classmethod
    def _handle_body_data_dict(
        self, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        raise NotImplementedError

    @classmethod
    def _handle_body_data_xml(
        cls, event_bus: EventBus, xml_message: str
    ) -> HandlingResult:
        element = ElementTree.fromstring(xml_message)

        if element.attrib.get("ret") != "ok":
            return HandlingResult.analyse()

        left = int(element.attrib.get("left"))
        total = int(element.attrib.get("total"))

        if total < 0:
            raise ValueError("total is not positive!")

        percentage = round((left / total) * 100, 2)
        event_bus.notify(LifeSpanEvent(LifeSpan.SIDE_BRUSH, percentage, left))

        return HandlingResult.success()


class GetLifeSpanHeap(CommandWithMessageHandling, MessageBodyDataDict):
    # As far as I know, there is no non-XML implementation for this
    name = "GetLifeSpanSideBrush"

    xml_name = "GetLifeSpan"

    def __init__(self) -> None:
        args = {"type": "DustCaseHeap"}
        super().__init__(args)

    @classmethod
    def _handle_body_data_dict(
        self, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        raise NotImplementedError

    @classmethod
    def _handle_body_data_xml(
        cls, event_bus: EventBus, xml_message: str
    ) -> HandlingResult:
        element = ElementTree.fromstring(xml_message)

        if element.attrib.get("ret") != "ok":
            return HandlingResult.analyse()

        left = int(element.attrib.get("left"))
        total = int(element.attrib.get("total"))

        if total < 0:
            raise ValueError("total is not positive!")

        percentage = round((left / total) * 100, 2)
        event_bus.notify(LifeSpanEvent(LifeSpan.FILTER, percentage, left))

        return HandlingResult.success()


class GetLifeSpan(CommandWithMessageHandling, MessageBodyDataList):
    """Get life span command."""

    name = "getLifeSpan"

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
