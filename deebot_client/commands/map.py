"""Maps commands."""
import logging
from typing import Any, Dict

from ..command import Command
from ..events.event_bus import EventBus
from ..events.map import MapTraceEventDto
from ..message import HandlingResult, HandlingState
from . import CommandWithHandling
from .common import CommandResult

_LOGGER = logging.getLogger(__name__)


class GetCachedMapInfo(Command):
    """Get cached map info command."""

    name = "getCachedMapInfo"

    def __init__(self) -> None:
        super().__init__()


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

    def __init__(self, *, map_id: int, piece_index: int) -> None:
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


class GetMajorMap(Command):
    """Get major map command."""

    name = "getMajorMap"

    def __init__(self) -> None:
        super().__init__()
