"""Map messages."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import MajorMapEvent, MapSetType, MapTraceEvent, MinorMapEvent
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataDict

_LOGGER = get_logger(__name__)

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnMajorMap(MessageBodyDataDict):
    """On major map message."""

    name = "onMajorMap"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        values = data["value"].split(",")
        map_id = data["mid"]

        event_bus.notify(MajorMapEvent(requested=True, map_id=map_id, values=values))
        return HandlingResult(
            HandlingState.SUCCESS, {"map_id": map_id, "values": values}
        )


class OnMapSetV2(MessageBodyDataDict):
    """On map set v2 message."""

    name = "onMapSet_V2"

    @classmethod
    def _handle_body_data_dict(
        cls, _: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        # check if type is known and mid is given
        if not MapSetType.has_value(data["type"]) or not data.get("mid"):
            return HandlingResult.analyse()

        # NOTE: here would be needed to call 'GetMapSetV2' again with 'mid' and 'type',
        #       that on event will update the map set changes,
        #       messages current cannot call commands again
        return HandlingResult(
            HandlingState.SUCCESS, {"mid": data["mid"], "type": data["type"]}
        )


class OnMapTrace(MessageBodyDataDict):
    """On map trace message."""

    name = "onMapTrace"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if not data.get("traceValue"):
            # TODO verify that this is legit pylint: disable=fixme
            return HandlingResult.analyse()

        total = int(data["totalCount"])
        start = int(data["traceStart"])

        event_bus.notify(
            MapTraceEvent(start=start, total=total, data=data["traceValue"])
        )
        return HandlingResult(HandlingState.SUCCESS, {"start": start, "total": total})


class OnMinorMap(MessageBodyDataDict):
    """On minor map message."""

    name = "onMinorMap"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        # onMinorMap sends no type, so fallback to "ol"
        if data.get("type", "ol") == "ol":
            event_bus.notify(MinorMapEvent(data["pieceIndex"], data["pieceValue"]))
            return HandlingResult.success()

        return HandlingResult.analyse()
