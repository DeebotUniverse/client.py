"""Position command module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import Position, PositionsEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict
from deebot_client.rs.map import PositionType

from .common import JsonCommandWithMessageHandling

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetPos(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get volume command."""

    NAME = "getPos"

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

        for type_str in ["deebotPos", "chargePos"]:
            data_positions = data.get(type_str, [])

            if isinstance(data_positions, dict):
                positions.append(
                    Position(
                        type=PositionType.from_str(type_str),
                        x=data_positions["x"],
                        y=data_positions["y"],
                        a=data_positions.get("a", 0),
                    )
                )
            else:
                positions.extend(
                    [
                        Position(
                            type=PositionType.from_str(type_str),
                            x=entry["x"],
                            y=entry["y"],
                            a=entry.get("a", 0),
                        )
                        for entry in data_positions
                    ]
                )

        if positions:
            event_bus.notify(PositionsEvent(positions=positions))
            return HandlingResult.success()

        return HandlingResult.analyse()
