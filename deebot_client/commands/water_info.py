"""Water info commands."""
import logging
from typing import Any, Dict, Mapping, Union

from ..events import WaterAmount, WaterInfoEventDto
from ..message import MessageResponse
from .common import EventBus, SetCommand, _NoArgsCommand

_LOGGER = logging.getLogger(__name__)


class GetWaterInfo(_NoArgsCommand):
    """Get water info command."""

    name = "getWaterInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: Dict[str, Any]
    ) -> MessageResponse:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        # todo enable can be missing pylint: disable=fixme
        mop_attached = bool(data.get("enable"))

        event_bus.notify(
            WaterInfoEventDto(mop_attached, WaterAmount(int(data["amount"])))
        )
        return MessageResponse.success()


class SetWaterInfo(SetCommand):
    """Set water info command."""

    name = "setWaterInfo"
    get_command = GetWaterInfo

    def __init__(
        self, amount: Union[str, int, WaterAmount], **kwargs: Mapping[str, Any]
    ) -> None:
        # removing "enable" as we don't can set it
        kwargs.pop("enable", None)

        if isinstance(amount, str):
            amount = WaterAmount.get(amount)
        if isinstance(amount, WaterAmount):
            amount = amount.value

        super().__init__({"amount": amount}, **kwargs)
