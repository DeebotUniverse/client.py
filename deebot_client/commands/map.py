"""Maps commands."""
import logging
from typing import Any, Dict, List

from ..command import Command
from ..events import MajorMapEvent, MapSetEvent, MapTraceEvent, MinorMapEvent, RoomEvent
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

        return HandlingResult(
            HandlingState.SUCCESS,
            {"map_id": map_id, "values": values},
        )

    def handle_requested(
        self, event_bus: EventBus, response: Dict[str, Any]
    ) -> CommandResult:
        """Handle response from a manual requested command.

        :return: A message response
        """
        result = super().handle_requested(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            event_bus.notify(MajorMapEvent(True, **result.args))
            return CommandResult.success()

        return result


class GetMapSet(CommandWithHandling):
    """Get map set command."""

    _ARGS_ID = "id"
    _ARGS_SET_ID = "set_id"
    _ARGS_TYPE = "type"
    _ARGS_SUBSETS = "subsets"

    name = "getMapSet"

    def __init__(self, map_id: str) -> None:
        super().__init__({"mid": map_id, "type": "ar"})

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: Dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        args = {
            cls._ARGS_ID: data["mid"],
            cls._ARGS_SET_ID: data["msid"],
            cls._ARGS_TYPE: data["type"],
            cls._ARGS_SUBSETS: data["subsets"],
        }
        event_bus.notify(MapSetEvent(len(args["subsets"])))
        return HandlingResult(HandlingState.SUCCESS, args)

    def handle_requested(
        self, event_bus: EventBus, response: Dict[str, Any]
    ) -> CommandResult:
        """Handle response from a manual requested command.

        :return: A message response
        """
        result = super().handle_requested(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            commands: List[Command] = []
            for subset in result.args[self._ARGS_SUBSETS]:
                commands.append(
                    GetMapSubSet(
                        map_id=result.args[self._ARGS_ID],
                        map_set_id=result.args[self._ARGS_SET_ID],
                        map_type=result.args[self._ARGS_TYPE],
                        map_subset_id=subset["mssid"],
                    )
                )
            return CommandResult(result.state, result.args, commands)

        return result


class GetMapSubSet(CommandWithHandling):
    """Get map subset command."""

    _ROOM_INT_TO_NAME = {
        0: "Default",
        1: "Living Room",
        2: "Dining Room",
        3: "Bedroom",
        4: "Study",
        5: "Kitchen",
        6: "Bathroom",
        7: "Laundry",
        8: "Lounge",
        9: "Storeroom",
        10: "Kids room",
        11: "Sunroom",
        12: "Corridor",
        13: "Balcony",
        14: "Gym",
    }

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

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: Dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if data["type"] == "ar":
            subtype = data.get("subtype", data.get("subType", None))

            if subtype is not None:
                event_bus.notify(
                    RoomEvent(
                        subtype=cls._ROOM_INT_TO_NAME[subtype],
                        id=int(data["mssid"]),
                        coordinates=data["value"],
                    )
                )

                return HandlingResult.success()

        return HandlingResult.analyse()


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
            MapTraceEvent(start=start, total=total, data=data["traceValue"])
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


class GetMinorMap(CommandWithHandling):
    """Get minor map command."""

    name = "getMinorMap"

    def __init__(self, *, map_id: str, piece_index: int) -> None:
        super().__init__({"mid": map_id, "type": "ol", "pieceIndex": piece_index})

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: Dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if data["type"] == "ol":
            event_bus.notify(MinorMapEvent(data["pieceIndex"], data["pieceValue"]))
            return HandlingResult.success()

        return HandlingResult.analyse()
