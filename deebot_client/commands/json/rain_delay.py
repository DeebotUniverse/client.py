"""Rain delay commands."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final

from deebot_client.command import InitParam

from .common import ExecuteCommand, JsonCommandMqttP2P

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

RAIN_DELAY_VALUES: Final = frozenset(range(0, 301, 30))


class SetRainDelay(ExecuteCommand, JsonCommandMqttP2P):
    """Set the rain sensor state and post-rain delay in minutes."""

    NAME = "setRainDelay"
    _mqtt_params = MappingProxyType(
        {"enable": InitParam(bool, "enabled"), "delay": InitParam(int)}
    )

    def __init__(self, enabled: bool, delay: int) -> None:
        if delay not in RAIN_DELAY_VALUES:
            message = f"Unsupported rain delay: {delay}"
            raise ValueError(message)
        super().__init__({"enable": 1 if enabled else 0, "delay": delay})

    def _handle_mqtt_p2p(self, event_bus: EventBus, response: dict[str, Any]) -> None:
        """Handle the acknowledgement; onRainDelay reports the resulting state."""
        self.handle(event_bus, response)
