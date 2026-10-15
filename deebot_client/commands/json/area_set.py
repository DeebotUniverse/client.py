"""Mowing area commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import orjson

from deebot_client.events.mower import MowingArea, MowingAreasEvent
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataDict
from deebot_client.rs.util import decompress_base64_data

from .common import JsonCommandWithMessageHandling
from .map import GetCachedMapInfo

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_AREA_TYPE = "ar"


class GetAreaSet(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get mowing areas of a map.

    The subsets are a compressed list of [id, id, name, ...] entries.
    """

    NAME = "getAreaSet"

    def __init__(self, map_id: str) -> None:
        super().__init__({"mid": map_id, "aid": "0", "type": _AREA_TYPE})

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if data.get("type") != _AREA_TYPE:
            return HandlingResult.analyse()

        subsets = orjson.loads(decompress_base64_data(data["subsets"]))
        event_bus.notify(
            MowingAreasEvent(
                [
                    MowingArea(
                        id=str(area[0]), name=str(area[2]), label=_get_label(area)
                    )
                    for area in subsets
                ]
            )
        )
        return HandlingResult.success()


def _get_label(area: list[Any]) -> tuple[float, float] | None:
    """Return the label position of the area (["1","1","Vorne","","-5300","1500",..])."""
    try:
        return (float(area[4]), float(area[5]))
    except IndexError, TypeError, ValueError:
        return None


class GetMowingAreas(GetCachedMapInfo):
    """Get the used map and afterwards the mowing areas of it."""

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> HandlingResult:
        """Handle response from a command.

        :return: A message response
        """
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            result.requested_commands.append(GetAreaSet(result.args["map_id"]))

        return result
