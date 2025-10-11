"""Major map commands."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.commands.json.common import (
    JsonGetCommand,
    JsonSetCommand,
)
from deebot_client.events import (
    MajorMapEvent,
)
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.messages.json.map import OnMajorMap

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetMajorMap(JsonGetCommand, OnMajorMap):
    """Get major map command."""

    NAME = "getMajorMap"

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> HandlingResult:
        """Handle response from a command.

        :return: A message response
        """
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            event_bus.notify(MajorMapEvent(requested=True, **result.args))

        return result

    @classmethod
    def handle_set_args(
        cls, event_bus: EventBus, args: dict[str, Any]
    ) -> HandlingResult:
        """Handle arguments of set command."""
        return cls._handle_body_data_dict(event_bus, {"value": ""} | args)


class SetMajorMap(JsonSetCommand):
    """Set major map command."""

    NAME = "setMajorMap"
    get_command = GetMajorMap
    _mqtt_params = MappingProxyType({"mid": InitParam(str, "map_id")})

    def __init__(self, map_id: str) -> None:
        super().__init__({"mid": map_id})
