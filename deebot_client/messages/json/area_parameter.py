"""Area parameter messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events import AreaParameter, AreaParameterEvent
from deebot_client.message import HandlingResult, MessageBodyDataDict

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class OnAreaParameter(MessageBodyDataDict):
    """On area parameter message."""

    NAME = "onAreaParameter"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers."""
        area_parameters = [
            AreaParameter(
                area_id=parameter["areaID"],
                mow_height_level=parameter["mowHeightLevel"],
                cut_mode=parameter["cutMode"],
                obstacle_height=parameter["obstacleHeight"],
                angle=parameter["angle"],
            )
            for parameter in data["areaParameters"]
        ]

        event_bus.notify(AreaParameterEvent(area_parameters))
        return HandlingResult.success()
