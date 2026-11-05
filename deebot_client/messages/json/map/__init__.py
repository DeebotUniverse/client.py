"""Map messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deebot_client.events.map import (
    CachedMapInfoEvent,
    MajorMapEvent,
    Map,
    MapInfoChunkEvent,
    MapInfoEvent,
    MapSetType,
)
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataDict
from deebot_client.rs.map import RotationAngle

from .cached_map_info import OnCachedMapInfo

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

__all__ = [
    "OnCachedMapInfo",
    "OnMajorMap",
    "OnMapInfoV2",
    "OnMapSetV2",
]


class OnMapSetV2(MessageBodyDataDict):
    """On map set v2 message."""

    NAME = "onMapSet_V2"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        # check if type is know and mid us given
        if not MapSetType.has_value(data["type"]) or not data.get("mid"):
            return HandlingResult.analyse()

        commands = []
        if map_cap := event_bus.capabilities.map:
            commands.append(map_cap.set.execute(data["mid"], MapSetType(data["type"])))

        return HandlingResult(HandlingState.SUCCESS, requested_commands=commands)


class OnMajorMap(MessageBodyDataDict):
    """On major map message."""

    NAME = "onMajorMap"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        values = [int(value) for value in data["value"].split(",") if value]
        map_id = data["mid"]

        event_bus.notify(MajorMapEvent(map_id, values, requested=False))

        return HandlingResult(
            HandlingState.SUCCESS,
            {"map_id": map_id, "values": values},
        )


class OnMapInfoV2(MessageBodyDataDict):
    """On map info v2 command."""

    NAME = "onMapInfo_V2"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers.

        :return: A message response
        """
        if "outlineVer" not in data:
            return cls._handle_without_outline_version(event_bus, data)

        if (outline_version := data["outlineVer"]) == "0":
            # Skip it as it will be sent for non-active maps
            return HandlingResult.success()
        if outline_version != "1":
            # Unsupported version
            return HandlingResult.analyse()

        event_bus.notify(MapInfoEvent(map_id=data["mid"], info=data["info"]))

        return HandlingResult.success()

    @classmethod
    def _handle_without_outline_version(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle the format without outlineVer.

        The map info is sent in chunks with the same batid. The response to
        getMapInfo_V2 contains only the map id and the amount of chunks.

        :return: A message response
        """
        if "batid" in data:
            return cls._handle_chunk(event_bus, data)

        map_id = data.get("mid")
        if not map_id or map_id == "0" or "serial" not in data:
            return HandlingResult.analyse()

        event_bus.notify(
            CachedMapInfoEvent(
                {
                    Map(
                        id=map_id,
                        name="",
                        using=True,
                        built=int(data["serial"]) > 0,
                        angle=RotationAngle.DEG_0,
                    )
                }
            )
        )
        return HandlingResult(HandlingState.SUCCESS, {"map_id": map_id})

    @classmethod
    def _handle_chunk(cls, event_bus: EventBus, data: dict[str, Any]) -> HandlingResult:
        """Handle a map info chunk.

        :return: A message response
        """
        # serial is the amount of chunks in the batch; index starts at 0
        total = int(data["serial"])
        index = int(data["index"])
        if total == 0:
            return HandlingResult.success()
        if index >= total:
            return HandlingResult.analyse()

        event_bus.notify(
            MapInfoChunkEvent(
                map_id=data["mid"],
                batch_id=data["batid"],
                index=index,
                total=total,
                info=data["info"],
            )
        )
        return HandlingResult.success()
