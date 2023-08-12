"""Water info commands."""
from collections.abc import Mapping
from typing import Any

from ..events import WaterAmount, WaterInfoEvent
from ..message import HandlingResult, MessageBodyDataDict
from .common import EventBus, NoArgsCommand, SetCommand


class GetWaterInfo(NoArgsCommand, MessageBodyDataDict):
    """Get water info command."""

    name = "getWaterInfo"

    xml_name = "GetWaterInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        mop_attached = data.get("enable", None)
        if mop_attached is not None:
            mop_attached = bool(mop_attached)

        event_bus.notify(WaterInfoEvent(mop_attached, WaterAmount(int(data["amount"]))))
        return HandlingResult.success()

    @classmethod
    def _handle_body_data_xml(cls, event_bus: EventBus, xml_message: str):
        raise NotImplementedError

class SetWaterInfo(SetCommand):
    """Set water info command."""

    name = "setWaterInfo"

    xml_name = "SetWaterInfo"

    get_command = GetWaterInfo

    def __init__(
        self, amount: str | int | WaterAmount, **kwargs: Mapping[str, Any]
    ) -> None:
        # removing "enable" as we don't can set it
        kwargs.pop("enable", None)

        if isinstance(amount, str):
            amount = WaterAmount.get(amount)
        if isinstance(amount, WaterAmount):
            amount = amount.value

        super().__init__({"amount": amount}, **kwargs)

    @classmethod
    def _handle_body_data_xml(cls, event_bus: EventBus, xml_message: str):
        raise NotImplementedError
