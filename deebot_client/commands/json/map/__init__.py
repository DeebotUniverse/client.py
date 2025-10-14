"""Maps commands."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import orjson

from deebot_client.commands.json.common import JsonCommandWithMessageHandling
from deebot_client.events import (
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MapTraceEvent,
    MinorMapEvent,
    RoomsEvent,
)
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataDict
from deebot_client.messages.json.map import OnMapInfoV2
from deebot_client.models import Room
from deebot_client.rs.util import decompress_base64_data

from .cached_map_info import GetCachedMapInfo
from .major_map import GetMajorMap, SetMajorMap

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

__all__ = [
    "GetCachedMapInfo",
    "GetMajorMap",
    "GetMapSet",
    "GetMapSetV2",
    "GetMapSubSet",
    "GetMapTrace",
    "GetMinorMap",
    "SetMajorMap",
]

_LOGGER = get_logger(__name__)


class GetMapSet(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get map set command."""

    _ARGS_ID = "id"
    _ARGS_SET_ID = "set_id"
    _ARGS_TYPE = "type"
    _ARGS_SUBSETS = "subsets"

    NAME = "getMapSet"

    def __init__(
        self,
        mid: str,
        type: (MapSetType | str) = MapSetType.ROOMS,  # noqa: A002
    ) -> None:
        if isinstance(type, MapSetType):
            type = type.value  # noqa: A001

        super().__init__({"mid": mid, "type": type})

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if not MapSetType.has_value(data["type"]) or not data.get("subsets"):
            return HandlingResult.analyse()

        return cls._handle_subsets(event_bus, data)

    @classmethod
    def _handle_subsets(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle subsets in message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        subset_ids = [int(subset["mssid"]) for subset in data["subsets"]]
        event_bus.notify(MapSetEvent(MapSetType(data["type"]), subset_ids))
        return cls._get_handling_success_with_subset_command_args(data, subset_ids)

    @classmethod
    def _get_handling_success_with_subset_command_args(
        cls, data: dict[str, Any], subset_ids: list[int]
    ) -> HandlingResult:
        """Return args for HandlingResult.SUCCESS with subset command."""
        return HandlingResult(
            HandlingState.SUCCESS,
            {
                cls._ARGS_ID: data["mid"],
                cls._ARGS_SET_ID: data.get("msid"),
                cls._ARGS_TYPE: data["type"],
                cls._ARGS_SUBSETS: subset_ids,
            },
        )

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> HandlingResult:
        """Handle response from a command.

        :return: A message response
        """
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            result.requested_commands.extend(
                [
                    GetMapSubSet(
                        mid=result.args[self._ARGS_ID],
                        msid=result.args[self._ARGS_SET_ID],
                        type=result.args[self._ARGS_TYPE],
                        mssid=subset,
                    )
                    for subset in result.args[self._ARGS_SUBSETS]
                ]
            )

        return result


class GetMapSubSet(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get map subset command."""

    _ROOM_NUM_TO_NAME = MappingProxyType(
        {
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
            # 15 custom; get name from name attribute
        }
    )

    NAME = "getMapSubSet"

    def __init__(
        self,
        *,
        mid: str | int,
        mssid: str | int,
        msid: str | int | None = None,
        type: (MapSetType | str) = MapSetType.ROOMS,  # noqa: A002
    ) -> None:
        if isinstance(type, MapSetType):
            type = type.value  # noqa: A001

        if msid is None and type == MapSetType.ROOMS.value:
            error_msid_type = f"msid is required when type='{MapSetType.ROOMS.value}'"
            raise ValueError(error_msid_type)

        super().__init__(
            {
                "mid": str(mid),
                "msid": str(msid),
                "type": type,
                "mssid": str(mssid),
            },
        )

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if MapSetType.has_value(data["type"]):
            name = data.get("name", "").strip()

            if not name and (subtype := data.get("subtype", data.get("subType"))):
                try:
                    name = cls._ROOM_NUM_TO_NAME.get(int(subtype), None)
                except ValueError:
                    _LOGGER.warning("Subtype is not a number", exc_info=True)
                    return HandlingResult.analyse()

            _type = MapSetType(data["type"])
            if _type == MapSetType.ROOMS and not name:
                _LOGGER.warning("Got room without a name")
                return HandlingResult.analyse()

            # This command is used by new and old bots
            if data.get("compress", 0) == 1:
                # Newer bot's return coordinates as base64 decoded string
                coordinates = decompress_base64_data(data["value"]).decode()
            else:
                # Older bot's return coordinates direct as comma/semicolon separated list
                coordinates = data["value"]

            event_bus.notify(
                MapSubsetEvent(
                    id=int(data["mssid"]),
                    type=_type,
                    coordinates=coordinates,
                    name=name,
                )
            )

            return HandlingResult.success()

        return HandlingResult.analyse()


class GetMapSetV2(GetMapSet):
    """Get map set v2 command."""

    NAME = "getMapSet_V2"

    @classmethod
    def _handle_subsets(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle subsets in message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        # subset is based64 7z compressed
        subsets = orjson.loads(decompress_base64_data(data["subsets"]).decode())

        match map_type := data["type"]:
            case MapSetType.ROOMS:
                return cls._handle_rooms_subsets(event_bus, data, subsets)

            case MapSetType.VIRTUAL_WALLS | MapSetType.NO_MOP_ZONES:
                subset_ids = []
                for subset in subsets:
                    mssid = subset.pop(0)  # first entry in list is mssid
                    if len(subset) % 2 != 0:
                        _ = subset.pop(0)  # second entry, if exists, always "1"
                    coordinates = str(subset)  # all other in list are coordinates

                    event_bus.notify(
                        MapSubsetEvent(
                            id=int(mssid),
                            type=MapSetType(map_type),
                            coordinates=coordinates,
                        )
                    )
                    subset_ids.append(int(mssid))

                event_bus.notify(MapSetEvent(MapSetType(map_type), subset_ids))
                return HandlingResult.success()

        return HandlingResult.analyse()

    @classmethod
    def _handle_rooms_subsets(
        cls,
        event_bus: EventBus,
        data: dict[str, Any],
        subsets: list[list[str]],
    ) -> HandlingResult:
        # there are two versions of this message, depending on the number of values
        if subsets and len(subsets[0]) == 10:
            # subset values
            # 1 -> id
            # 2 -> name
            # 3 -> icon number
            # 4 -> unknown
            # 5 -> unknown
            # 6 -> room center x
            # 7 -> room center y
            # 8 -> room clean configs as '<count>-<speed>-<water>'
            # 9 -> unknown
            # 10 -> floor type

            # coordinates are sent in the MapInfo_V2 message
            event_bus.notify(
                RoomsEvent([Room(subset[1], int(subset[0]), "") for subset in subsets])
            )

            # GetMapSubSet isn't supported for this robot and not needed
            return HandlingResult.success()

        # subset values
        # 1 -> id
        # 2 -> unknown
        # 3 -> unknown
        # 4 -> room clean order
        # 5 -> room center x
        # 6 -> room center y
        # 7 -> room clean configs as '<count>-<speed>-<water>'
        # 8 -> named all as 'settingName1'
        # return the subset ids to trigger GetMapSubSet for each one
        subset_ids = [int(subset[0]) for subset in subsets]
        event_bus.notify(MapSetEvent(MapSetType.ROOMS, subset_ids))
        return cls._get_handling_success_with_subset_command_args(data, subset_ids)


class GetMapTrace(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get map trace command."""

    _TRACE_POINT_COUNT = 200

    NAME = "getMapTrace"

    def __init__(self, trace_start: int = 0) -> None:
        super().__init__(
            {"pointCount": self._TRACE_POINT_COUNT, "traceStart": trace_start},
        )

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        total = int(data["totalCount"])
        start = int(data["traceStart"])

        if "traceValue" not in data:
            # TODO verify that this is legit
            return HandlingResult.analyse()

        event_bus.notify(
            MapTraceEvent(start=start, total=total, data=data["traceValue"])
        )
        return HandlingResult(HandlingState.SUCCESS, {"start": start, "total": total})

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> HandlingResult:
        """Handle response from a command.

        :return: A message response
        """
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            start = result.args["start"] + self._TRACE_POINT_COUNT
            if start < result.args["total"]:
                result.requested_commands.append(GetMapTrace(start))

        return result


class GetMinorMap(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get minor map command."""

    NAME = "getMinorMap"

    def __init__(self, piece_index: int, map_id: str) -> None:
        super().__init__({"mid": map_id, "type": "ol", "pieceIndex": piece_index})

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if data.get("type", "ol") == "ol":
            # onMinorMap sends no type, so fallback to "ol"
            event_bus.notify(MinorMapEvent(data["pieceIndex"], data["pieceValue"]))
            return HandlingResult.success()

        return HandlingResult.analyse()


class GetMapInfoV2(JsonCommandWithMessageHandling, OnMapInfoV2):
    """Get map info v2 command."""

    NAME = "getMapInfo_V2"

    def __init__(self, map_id: str = "") -> None:
        super().__init__({"mid": map_id, "type": "0"})
