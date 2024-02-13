"""Map set v2 messages."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from deebot_client.events.map import MapSetEvent, MapSetType, MapSubsetEvent
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataDict
from deebot_client.util import decompress_7z_base64_data

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnMapSetV2(MessageBodyDataDict):
    """On map set v2 message."""

    name = "onMapSet_V2"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        # check if type is know
        if not MapSetType.has_value(data["type"]):
            return HandlingResult.analyse()

        # if subsets is not given, it was an event/atr handling (this is to be done)
        if not data.get("subsets") and data.get("mid"):
            # NOTE: here would be needed to call 'GetMapSetV2' again with 'mid' and 'type',
            #       that on event will update the map set changes,
            #       messages current cannot call commands again
            return HandlingResult(
                HandlingState.SUCCESS, {"mid": data["mid"], "type": data["type"]}
            )

        # subset is based64 7z compressed
        subsets: list[list[str]] = json.loads(
            decompress_7z_base64_data(data["subsets"]).decode()
        )

        # handle rooms
        if data["type"] in (MapSetType.ROOMS):
            room_subsets: list[dict[str, Any]] = [
                {
                    "id": int(subset[0]),  # room id
                    "name": subset[1]
                    if subset[1] and subset[1] != " "
                    else "Default",  # room name
                    # subset[2] not sure what the value is for
                    # subset[3] not sure what the value is for
                    # subset[4] room clean order
                    "coordinates": f"{subset[5]},{subset[6]}",  # room center coordinates
                    # subset[7] room clean configs as '<count>-<speed>-<water>'
                    # subset[8] named all as 'settingName1'
                }
                for subset in subsets
            ]

            # notify first MapSetType to set room count
            event_bus.notify(
                MapSetEvent(
                    MapSetType(data["type"]), [subset["id"] for subset in room_subsets]
                )
            )

            # afterwards notify MapSubsetEvent to set room details
            for room in room_subsets:
                event_bus.notify(
                    MapSubsetEvent(
                        id=room["id"],
                        type=MapSetType(data["type"]),
                        coordinates=room["coordinates"],
                        name=room["name"],
                    )
                )

        # virtual walls and no map zones are same handled
        if data["type"] in (MapSetType.VIRTUAL_WALLS, MapSetType.NO_MOP_ZONES):
            for subset in subsets:
                mssid = subset[0]  # first entry in list is mssid
                coordinates = str(subset[1:])  # all other in list are coordinates

                event_bus.notify(
                    MapSubsetEvent(
                        id=int(mssid),
                        type=MapSetType(data["type"]),
                        coordinates=coordinates,
                    )
                )

        return HandlingResult.success()
