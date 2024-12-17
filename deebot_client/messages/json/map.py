"""Map set v2 messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.map import MapSetType
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnMapSetV2(MessageBodyDataDict):
    """On map set v2 message."""

    NAME = "onMapSet_V2"

    @classmethod
    def _handle_body_data_dict(
        cls, _: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        # check if type is know and mid us given
        if not MapSetType.has_value(data["type"]) or not data.get("mid"):
            return HandlingResult.analyse()

        # NOTE: here would be needed to call 'GetMapSetV2' again with 'mid' and 'type',
        #       that on event will update the map set changes,
        #       messages current cannot call commands again
        return HandlingResult(
            HandlingState.SUCCESS, {"mid": data["mid"], "type": data["type"]}
        )
