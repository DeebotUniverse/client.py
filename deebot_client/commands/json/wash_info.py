"""WashInfo command module."""

from types import MappingProxyType
from typing import Any

from deebot_client.command import InitParam
from deebot_client.event_bus import EventBus
from deebot_client.events import WashInfoEvent, WashMode
from deebot_client.message import HandlingResult

from .common import JsonGetCommand, JsonSetCommand


class GetWashInfo(JsonGetCommand):
    """Get wash info command."""

    name = "getWashInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(
            WashInfoEvent(
                mode=WashMode(int(data["mode"])),
                hot_wash_amount=data["hot_wash_amount"],
                interval=data["interval"],
            )
        )
        return HandlingResult.success()


class SetWashInfoMode(JsonSetCommand):
    """Set wash info command for mode."""

    name = "setWashInfo"
    get_command = GetWashInfo
    _mqtt_params = MappingProxyType(
        {
            "mode": InitParam(int),
        }
    )

    def __init__(self, mode: WashMode | str) -> None:
        if isinstance(mode, str):
            mode = WashMode.get(mode)
        super().__init__({"mode": mode.value})


class SetWashInfoHotWashAmount(JsonSetCommand):
    """Set wash info command for hot_wash_amount."""

    name = "setWashInfo"
    get_command = GetWashInfo
    _mqtt_params = MappingProxyType(
        {
            "hot_wash_amount": InitParam(int),
        }
    )

    def __init__(self, hot_wash_amount: int) -> None:
        super().__init__({"hot_wash_amount": hot_wash_amount})
