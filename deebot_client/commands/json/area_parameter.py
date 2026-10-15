"""Area parameter commands."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import replace
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events.mower import (
    AreaParameter,
    AreaParametersEvent,
    ObstacleHeight,
)
from deebot_client.message import HandlingResult

from .common import JsonGetCommand, JsonSetCommand

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


def _get_area_parameter(data: dict[str, Any]) -> AreaParameter:
    obstacle_height: ObstacleHeight | int = int(data["obstacleHeight"])
    with suppress(ValueError):
        obstacle_height = ObstacleHeight(obstacle_height)
    return AreaParameter(
        area_id=str(data["areaID"]),
        cut_height=int(data["mowHeightLevel"]),
        cut_mode=int(data["cutMode"]),
        obstacle_height=obstacle_height,
    )


class GetAreaParameter(JsonGetCommand):
    """Get area parameter command."""

    NAME = "getAreaParameter"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        event_bus.notify(
            AreaParametersEvent(
                [_get_area_parameter(area) for area in data["areaParameters"]]
            )
        )
        return HandlingResult.success()

    @classmethod
    def handle_set_args(
        cls, event_bus: EventBus, args: dict[str, Any]
    ) -> HandlingResult:
        """Handle arguments of set command.

        The set command contains only one area, therefore merge it with the last event.
        """
        area = _get_area_parameter(args)
        if last := event_bus.get_last_event(AreaParametersEvent):
            areas = [a for a in last.areas if a.area_id != area.area_id]
            areas.append(area)
            areas.sort(key=lambda a: a.area_id)
            event_bus.notify(replace(last, areas=areas))
        else:
            event_bus.notify(AreaParametersEvent([area]))
        return HandlingResult.success()


class SetAreaParameter(JsonSetCommand):
    """Set area parameter command."""

    NAME = "setAreaParameter"
    get_command = GetAreaParameter
    _mqtt_params = MappingProxyType(
        {
            "areaID": InitParam(str, "area_id"),
            "mowHeightLevel": InitParam(int, "cut_height"),
            "cutMode": InitParam(int, "cut_mode"),
            "obstacleHeight": InitParam(int, "obstacle_height"),
        }
    )

    def __init__(
        self, area_id: str, cut_height: int, cut_mode: int, obstacle_height: int
    ) -> None:
        super().__init__(
            {
                "areaID": area_id,
                "mowHeightLevel": cut_height,
                "cutMode": cut_mode,
                "obstacleHeight": int(obstacle_height),
            }
        )
