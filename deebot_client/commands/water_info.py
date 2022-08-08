"""Water info commands."""
from collections.abc import Mapping
from typing import Any

from ..events import WaterAmount, WaterInfoEvent
from ..message import HandlingResult
from .common import EventBus, SetCommand, _NoArgsCommand


class GetWaterInfo(_NoArgsCommand):
    """Get water info command."""

    name = "getWaterInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        # todo enable can be missing pylint: disable=fixme
        mop_attached = bool(data.get("enable"))

        event_bus.notify(WaterInfoEvent(mop_attached, WaterAmount(int(data["amount"]))))
        return HandlingResult.success()


class SetWaterInfo(SetCommand):
    """Set water info command."""

    name = "setWaterInfo"
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
