"""Maps commands."""
import logging
from typing import Any, Dict

from ..command import Command
from ..events import MajorMapEventDto, MapTraceEventDto
from ..events.event_bus import EventBus
from ..message import HandlingResult, HandlingState
from . import CommandWithHandling
from .common import CommandResult

_LOGGER = logging.getLogger(__name__)


class GetCachedMapInfo(CommandWithHandling):
    """Get cached map info command."""

    name = "getCachedMapInfo"

    def __init__(self) -> None:
        super().__init__()

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: Dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        for map_status in data["info"]:
            if map_status["using"] == 1:
                return HandlingResult(
                    HandlingState.SUCCESS, {"map_id": map_status["mid"]}
                )

        return HandlingResult.analyse()

    def handle_requested(
        self, event_bus: EventBus, response: Dict[str, Any]
    ) -> CommandResult:
        """Handle response from a manual requested command.

        :return: A message response
        """
        result = super().handle_requested(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            return CommandResult(
                result.state, result.args, [GetMapSet(result.args["map_id"])]
            )

        return result


class GetMajorMap(CommandWithHandling):
    """Get major map command."""

    _ARGS_DATA = "data"

    name = "getMajorMap"

    def __init__(self) -> None:
        super().__init__()

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: Dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        values = data["value"].split(",")
        map_id = data["mid"]

        event_bus.notify(MajorMapEventDto(False, map_id, values))
        return HandlingResult(
            HandlingState.SUCCESS,
            {cls._ARGS_DATA: {"map_id": map_id, "values": values}},
        )

    def handle_requested(
        self, event_bus: EventBus, response: Dict[str, Any]
    ) -> CommandResult:
        """Handle response from a manual requested command.

        :return: A message response
        """
        result = super().handle_requested(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            event_bus.notify(MajorMapEventDto(True, **result.args[self._ARGS_DATA]))
            return CommandResult.success()

        return result


class GetMapTrace(CommandWithHandling):
    """Get map trace command."""

    _TRACE_POINT_COUNT = 200

    name = "getMapTrace"

    def __init__(self, trace_start: int = 0) -> None:
        super().__init__(
            {"pointCount": self._TRACE_POINT_COUNT, "traceStart": trace_start},
        )

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: Dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        total = int(data["totalCount"])
        start = int(data["traceStart"])

        if "traceValue" not in data:
            # todo verify that this is legit pylint: disable=fixme
            return HandlingResult.analyse()

        event_bus.notify(
            MapTraceEventDto(start=start, total=total, data=data["traceValue"])
        )
        return HandlingResult(HandlingState.SUCCESS, {"start": start, "total": total})

    def handle_requested(
        self, event_bus: EventBus, response: Dict[str, Any]
    ) -> CommandResult:
        """Handle response from a manual requested command.

        :return: A message response
        """
        result = super().handle_requested(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            start = result.args["start"] + self._TRACE_POINT_COUNT
            if start < result.args["total"]:
                return CommandResult(result.state, result.args, [GetMapTrace(start)])

        return result


class GetMinorMap(Command):
    """Get minor map command."""

    name = "getMinorMap"

    def __init__(self, *, map_id: str, piece_index: int) -> None:
        super().__init__({"mid": map_id, "type": "ol", "pieceIndex": piece_index})


class GetMapSet(Command):
    """Get map set command."""

    name = "getMapSet"

    def __init__(self, map_id: str) -> None:
        super().__init__({"mid": map_id, "type": "ar"})


class GetMapSubSet(Command):
    """Get map subset command."""

    name = "getMapSubSet"

    def __init__(
        self, *, map_id: str, map_set_id: str, map_type: str, map_subset_id: str
    ) -> None:
        super().__init__(
            {
                "mid": map_id,
                "msid": map_set_id,
                "type": map_type,
                "mssid": map_subset_id,
            },
        )
