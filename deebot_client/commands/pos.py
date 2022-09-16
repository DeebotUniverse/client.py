"""Position command module."""

from typing import Any

from ..events import Position, PositionsEvent, PositionType
from ..message import HandlingResult, MessageBodyDataDict
from .common import CommandWithHandling, EventBus


class GetPos(CommandWithHandling, MessageBodyDataDict):
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
                for entry in data_positions:
                    positions.append(
                        Position(
                            type=PositionType(type_str), x=entry["x"], y=entry["y"]
                        )
                    )

        if positions:
            event_bus.notify(PositionsEvent(positions=positions))
            return HandlingResult.success()

        return HandlingResult.analyse()
