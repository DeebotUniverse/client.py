"""Cached map info commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.commands.json.common import JsonCommandWithMessageHandling
from deebot_client.events import (
    MapSetType,
)
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.messages.json.map.cached_map_info import OnCachedMapInfo

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetCachedMapInfo(JsonCommandWithMessageHandling, OnCachedMapInfo):
    """Get cached map info command."""

    NAME = "getCachedMapInfo"

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> HandlingResult:
        """Handle response from a command.

        :return: A message response
        """
        result = super()._handle_response(event_bus, response)
        if (
            result.state == HandlingState.SUCCESS
            and result.args
            and (map_obj := event_bus.capabilities.map)
        ):
            map_id = result.args["map_id"]
            result.requested_commands.extend(
                [map_obj.set.execute(map_id, entry) for entry in MapSetType]
            )

            if map_obj.info:
                result.requested_commands.append(map_obj.info.execute(map_id))

        return result
