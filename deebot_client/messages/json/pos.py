"""Position messages."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import Position, PositionsEvent, PositionType
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnPos(MessageBodyDataDict):
    """On pos message."""

    name = "onPos"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        positions = []

        for type_str in ["deebotPos", "chargePos"]:
            data_positions = data.get(type_str, [])

            if isinstance(data_positions, dict):
                positions.append(
                    Position(
                        type=PositionType(type_str),
                        x=data_positions["x"],
                        y=data_positions["y"],
                    )
                )
            else:
                positions.extend(
                    [
                        Position(
                            type=PositionType(type_str), x=entry["x"], y=entry["y"]
                        )
                        for entry in data_positions
                    ]
                )

        if len(positions) > 0:
            event_bus.notify(PositionsEvent(positions=positions))
            return HandlingResult.success()

        return HandlingResult.analyse()
