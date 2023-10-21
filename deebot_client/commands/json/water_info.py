"""Water info commands."""
from typing import Any

from deebot_client.command import InitParam
from deebot_client.event_bus import EventBus
from deebot_client.events import WaterAmount, WaterInfoEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import CommandWithMessageHandling, SetCommand


class GetWaterInfo(CommandWithMessageHandling, MessageBodyDataDict):
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
    def _handle_body_data_xml(
        cls, event_bus: EventBus, xml_message: str
    ) -> HandlingResult:
        raise NotImplementedError


class SetWaterInfo(SetCommand):
    """Set water info command."""

    name = "setWaterInfo"

    xml_name = "SetWaterInfo"

    get_command = GetWaterInfo
    _mqtt_params = {
        "amount": InitParam(WaterAmount),
        "enable": None,  # Remove it as we don't can set it (App includes it)
    }

    def __init__(self, amount: WaterAmount | str) -> None:
        if isinstance(amount, str):
            amount = WaterAmount.get(amount)
        super().__init__({"amount": amount.value})
