"""Water info commands."""
import logging
from typing import Any, Dict, Mapping, Union

from ..events import WaterAmount, WaterInfoEventDto
from .common import EventBus, SetCommand, _NoArgsCommand

_LOGGER = logging.getLogger(__name__)


class GetWaterInfo(_NoArgsCommand):
    """Get water info command."""

    name = "getWaterInfo"

    @classmethod
    def _handle_body_data_dict(cls, event_bus: EventBus, data: Dict[str, Any]) -> bool:
        """Handle message->body->data and notify the correct event subscribers.

        :return: True if data was valid and no error was included
        """
        amount = data.get("amount", None)
        mop_attached = bool(data.get("enable"))

        if amount is not None:
            try:
                event_bus.notify(
                    WaterInfoEventDto(mop_attached, WaterAmount(int(amount)))
                )
                return True
            except ValueError:
                _LOGGER.warning("Could not parse correctly water info amount: %s", data)

        _LOGGER.warning("Could not parse %s with %s", cls.name, data)
        return False


class SetWaterInfo(SetCommand):
    """Set water info command."""

    name = "setWaterInfo"
    get_command = GetWaterInfo

    def __init__(
        self, amount: Union[str, int, WaterAmount], **kwargs: Mapping[str, Any]
    ) -> None:
        # removing "enable" as we don't can set it
        remove_from_kwargs = ["enable"]
        if isinstance(amount, str):
            amount = WaterAmount.get(amount)
        if isinstance(amount, WaterAmount):
            amount = amount.value

        super().__init__({"amount": amount, "enable": 0}, remove_from_kwargs, **kwargs)
