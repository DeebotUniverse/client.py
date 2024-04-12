"""Water info commands."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import WaterAmount, WaterInfoEvent
from deebot_client.message import HandlingResult
from deebot_client.util import get_enum

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetWaterInfo(JsonGetCommand):
    """Get water info command."""

    name = "getWaterInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        mop_attached = data.get("enable")
        if mop_attached is not None:
            mop_attached = bool(mop_attached)

        event_bus.notify(
            WaterInfoEvent(WaterAmount(int(data["amount"])), mop_attached=mop_attached)
        )
        return HandlingResult.success()


class SetWaterInfo(JsonSetCommand):
    """Set water info command."""

    name = "setWaterInfo"
    get_command = GetWaterInfo
    _mqtt_params = MappingProxyType(
        {
            "amount": InitParam(WaterAmount),
            "enable": None,  # Remove it as we don't can set it (App includes it)
        }
    )

    def __init__(self, amount: WaterAmount | str) -> None:
        if isinstance(amount, str):
            amount = get_enum(WaterAmount, amount)
        super().__init__({"amount": amount.value})
