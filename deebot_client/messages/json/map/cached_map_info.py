"""Cached map info messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.map import CachedMapInfoEvent, Map
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataDict
from deebot_client.rs.map import RotationAngle

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


_LOGGER = get_logger(__name__)


class OnCachedMapInfo(MessageBodyDataDict):
    """On cached map info message."""

    NAME = "onCachedMapInfo"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        map_using: Map | None = None
        maps: set[Map] = set()
        for map_info in data["info"]:
            if (map_id := map_info["mid"]) == "0":
                _LOGGER.debug("Ignoring map with id 0")
                continue

            map_obj = Map(
                id=map_id,
                name=map_info.get("name", ""),
                using=map_info["using"] == 1,
                built=map_info["built"] == 1,
                angle=RotationAngle.from_int(map_info.get("angle", 0)),
            )
            maps.add(map_obj)
            if map_obj.using:
                map_using = map_obj

        if maps:
            event_bus.notify(CachedMapInfoEvent(maps=maps))
        if map_using:
            return HandlingResult(HandlingState.SUCCESS, {"map_id": map_using.id})

        return HandlingResult.analyse()
