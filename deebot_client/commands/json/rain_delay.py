"""Rain delay module."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import RainDelayEvent
from deebot_client.message import HandlingResult

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetRainDelay(JsonGetCommand):
    """Get cut direction command."""

    NAME = "getRainDelay"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(RainDelayEvent(enable=data["enable"], delay=data["delay"]))
        return HandlingResult.success()


class SetRainDelay(JsonSetCommand):
    """Set rain delay command."""

    NAME = "setRainDelay"
    get_command = GetRainDelay
    _mqtt_params = MappingProxyType(
        {"enable": InitParam(bool), "delay": InitParam(int)}
    )

    def __init__(self, enable: bool, delay: int) -> None:
        super().__init__({"enable": enable, "delay": delay})
