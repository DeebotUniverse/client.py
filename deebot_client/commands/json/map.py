"""Maps commands."""
from __future__ import annotations

import json
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import Command, CommandResult
from deebot_client.events import (
    MajorMapEvent,
    MapSetEvent,
    MapSetType,
    MapSubsetEvent,
    MapTraceEvent,
    MinorMapEvent,
)
from deebot_client.events.map import CachedMapInfoEvent
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataDict
from deebot_client.util import decompress_7z_base64_data

from .common import JsonCommandWithMessageHandling

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


class GetCachedMapInfo(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get cached map info command."""

    name = "getCachedMapInfo"
    # version definition for using type of getMapSet v1 or v2
    _map_set_command: type[GetMapSet | GetMapSetV2]

    def __init__(
        self, args: dict[str, Any] | list[Any] | None = None, version: int = 1
    ) -> None:
        match version:
            case 1:
                self._map_set_command = GetMapSet
            case 2:
                self._map_set_command = GetMapSetV2
            case _:
                error_wrong_version = f"version={version} is not supported"
                raise ValueError(error_wrong_version)

        super().__init__(args)

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        for map_status in data["info"]:
            if map_status["using"] == 1:
                event_bus.notify(
                    CachedMapInfoEvent(name=map_status.get("name", ""), active=True)
                )

                return HandlingResult(
                    HandlingState.SUCCESS, {"map_id": map_status["mid"]}
                )

        return HandlingResult.analyse()

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            return CommandResult(
                result.state,
                result.args,
                [
                    self._map_set_command(result.args["map_id"], entry)
                    for entry in MapSetType
                ],
            )

        return result


class GetMajorMap(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get major map command."""

    name = "getMajorMap"

    @classmethod
    def _handle_body_data_dict(
        cls, _: EventBus, data: dict[str, Any]
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

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            event_bus.notify(MajorMapEvent(requested=True, **result.args))
            return CommandResult.success()

        return result


class GetMapSet(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get map set command."""

    _ARGS_ID = "id"
    _ARGS_SET_ID = "set_id"
    _ARGS_TYPE = "type"
    _ARGS_SUBSETS = "subsets"

    name = "getMapSet"

    def __init__(
        self,
        mid: str,
        type: (  # pylint: disable=redefined-builtin
            MapSetType | str
        ) = MapSetType.ROOMS,
    ) -> None:
        if isinstance(type, MapSetType):
            type = type.value

        super().__init__({"mid": mid, "type": type})

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        subsets = [int(subset["mssid"]) for subset in data["subsets"]]
        args = {
            cls._ARGS_ID: data["mid"],
            cls._ARGS_SET_ID: data.get("msid"),
            cls._ARGS_TYPE: data["type"],
            cls._ARGS_SUBSETS: subsets,
        }

        event_bus.notify(MapSetEvent(MapSetType(data["type"]), subsets))
        return HandlingResult(HandlingState.SUCCESS, args)

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            commands: list[Command] = [
                GetMapSubSet(
                    mid=result.args[self._ARGS_ID],
                    msid=result.args[self._ARGS_SET_ID],
                    type=result.args[self._ARGS_TYPE],
                    mssid=subset,
                )
                for subset in result.args[self._ARGS_SUBSETS]
            ]
            return CommandResult(result.state, result.args, commands)

        return result


class GetMapSubSet(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get map subset command."""

    _ROOM_NUM_TO_NAME = MappingProxyType(
        {
            "0": "Default",
            "1": "Living Room",
            "2": "Dining Room",
            "3": "Bedroom",
            "4": "Study",
            "5": "Kitchen",
            "6": "Bathroom",
            "7": "Laundry",
            "8": "Lounge",
            "9": "Storeroom",
            "10": "Kids room",
            "11": "Sunroom",
            "12": "Corridor",
            "13": "Balcony",
            "14": "Gym",
            # 15 custom; get name from name attribute
        }
    )

    name = "getMapSubSet"

    def __init__(
        self,
        *,
        mid: str | int,
        mssid: str | int,
        msid: str | int | None = None,
        type: (  # pylint: disable=redefined-builtin
            MapSetType | str
        ) = MapSetType.ROOMS,
    ) -> None:
        if isinstance(type, MapSetType):
            type = type.value

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
            subtype = data.get("subtype", data.get("subType"))
            name = None
            if subtype == "15":
                name = data.get("name")
            elif subtype:
                name = cls._ROOM_NUM_TO_NAME.get(subtype, None)

            event_bus.notify(
                MapSubsetEvent(
                    id=int(data["mssid"]),
                    type=MapSetType(data["type"]),
                    coordinates=data["value"],
                    name=name,
                )
            )

            return HandlingResult.success()

        return HandlingResult.analyse()


class GetMapSetV2(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get map set v2 command."""

    name = "getMapSet_V2"

    def __init__(
        self,
        mid: str,
        type: (  # pylint: disable=redefined-builtin
            MapSetType | str
        ) = MapSetType.ROOMS,
    ) -> None:
        if isinstance(type, MapSetType):
            type = type.value

        super().__init__({"mid": mid, "type": type})

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        # check if type is know
        if not MapSetType.has_value(data["type"]):
            return HandlingResult.analyse()

        # if subsets is not given, it was an event/atr handling (this is to be done)
        if not data.get("subsets") and data.get("mid"):
            return HandlingResult(
                HandlingState.SUCCESS, {"mid": data["mid"], "type": data["type"]}
            )

        # subset is based64 7z compressed
        subsets: list[list[str]] = json.loads(
            decompress_7z_base64_data(data["subsets"]).decode()
        )

        # handle rooms
        if data["type"] in (MapSetType.ROOMS):
            room_subsets: list[dict[str, Any]] = [
                {
                    "id": int(subset[0]),  # room id
                    "name": subset[1]
                    if subset[1] and subset[1] != " "
                    else "Default",  # room name
                    # subset[2] not sure what the value is for
                    # subset[3] not sure what the value is for
                    # subset[4] room clean order
                    "coordinates": f"{subset[5]},{subset[6]}",  # room center coordinates
                    # subset[7] room clean configs as '<count>-<speed>-<water>'
                    # subset[8] named all as 'settingName1'
                }
                for subset in subsets
            ]

            # notify first MapSetType to set room count
            event_bus.notify(
                MapSetEvent(
                    MapSetType(data["type"]), [subset["id"] for subset in room_subsets]
                )
            )

            # afterwards notify MapSubsetEvent to set room details
            for room in room_subsets:
                event_bus.notify(
                    MapSubsetEvent(
                        id=room["id"],
                        type=MapSetType(data["type"]),
                        coordinates=room["coordinates"],
                        name=room["name"],
                    )
                )

        # virtual walls and no map zones are same handled
        if data["type"] in (MapSetType.VIRTUAL_WALLS, MapSetType.NO_MOP_ZONES):
            for subset in subsets:
                mssid = subset[0]  # first entry in list is mssid
                coordinates = str(subset[1:])  # all other in list are coordinates

                event_bus.notify(
                    MapSubsetEvent(
                        id=int(mssid),
                        type=MapSetType(data["type"]),
                        coordinates=coordinates,
                    )
                )

        return HandlingResult.success()

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            return CommandResult(
                result.state,
                result.args,
                [GetMapSetV2(result.args["mid"], result.args["type"])],
            )

        return result


class GetMapTrace(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get map trace command."""

    _TRACE_POINT_COUNT = 200

    name = "getMapTrace"

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
            # TODO verify that this is legit pylint: disable=fixme
            return HandlingResult.analyse()

        event_bus.notify(
            MapTraceEvent(start=start, total=total, data=data["traceValue"])
        )
        return HandlingResult(HandlingState.SUCCESS, {"start": start, "total": total})

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> CommandResult:
        """Handle response from a command.

        :return: A message response
        """
        result = super()._handle_response(event_bus, response)
        if result.state == HandlingState.SUCCESS and result.args:
            start = result.args["start"] + self._TRACE_POINT_COUNT
            if start < result.args["total"]:
                return CommandResult(result.state, result.args, [GetMapTrace(start)])

        return result


class GetMinorMap(JsonCommandWithMessageHandling, MessageBodyDataDict):
    """Get minor map command."""

    name = "getMinorMap"

    def __init__(self, *, map_id: str, piece_index: int) -> None:
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
