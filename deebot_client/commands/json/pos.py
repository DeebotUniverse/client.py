"""Position command module."""

from typing import Any

from deebot_client.event_bus import EventBus
from deebot_client.events import Position, PositionsEvent, PositionType
from deebot_client.message import HandlingResult, MessageBodyDataDict

from .common import JsonCommandWithMessageHandling

from shapely.geometry import Point

class GetPos(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get volume command."""

    name = "getPos"

    def __init__(self) -> None:
        super().__init__(["chargePos", "deebotPos"])

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        positions = []

        rooms = data.get("rooms", [])

        for type_str in ["deebotPos", "chargePos"]:

            room_name = None
            data_positions = data.get(type_str, [])

            if isinstance(data_positions, dict):
                point = Point(data_positions.get("x"), data_positions.get("y"))
                for room in rooms:
                    if room.polygon is not None and room.polygon.contains(point):
                        room_name = room.name
                        break

                positions.append(
                    Position(
                        type=PositionType(type_str),
                        x=data_positions.get("x"),
                        y=data_positions.get("y"),
                        room=room_name
                    )
                )
            else:
                for entry in data_positions:
                    point = Point(entry.get("x"), entry.get("y"))
                    for room in rooms:
                        if room.polygon is not None and room.polygon.contains(point):
                            room_name = room.name
                            break

                    positions.append(
                        Position(
                            type=PositionType(type_str),
                            x=entry.get("x"),
                            y=entry.get("y"),
                            room=room_name
                        )
                    )

        if positions:
            event_bus.notify(PositionsEvent(positions=positions))
            return HandlingResult.success()

        return HandlingResult.analyse()
