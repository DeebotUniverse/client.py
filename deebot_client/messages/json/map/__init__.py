"""Map messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import orjson

from deebot_client.events.map import (
    MajorMapEvent,
    MapInfoEvent,
    MapSetType,
    MapTraceEvent,
)
from deebot_client.logging_filter import get_logger
from deebot_client.message import HandlingResult, HandlingState, MessageBodyDataDict
from deebot_client.rs.util import decompress_base64_data

from .cached_map_info import OnCachedMapInfo

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)

__all__ = [
    "OnCachedMapInfo",
    "OnMajorMap",
    "OnMapInfoV2",
    "OnMapSetV2",
    "OnMapTrace",
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
        if (outline_version := data.get("outlineVer")) == "0":
            # Skip it as it will be sent for non-active maps
            return HandlingResult.success()
        if outline_version != "1":
            # Unsupported version
            return HandlingResult.analyse()

        event_bus.notify(MapInfoEvent(map_id=data["mid"], info=data["info"]))

        return HandlingResult.success()


class OnMapTrace(MessageBodyDataDict):
    """On map trace message — variant pushed by mower firmwares (e.g. GOAT 1.15.x).

    The vacuum-style ``getMapTrace`` response carried ``traceValue`` directly.
    Mower firmwares instead push a compressed envelope:

    .. code-block:: json

        {
            "mid": "...", "batid": "...", "serial": "1",
            "index": "0", "type": "4",
            "info": "<base64 of LZMA-compressed JSON>",
            "infoSize": 3455
        }

    The decompressed payload is itself a small JSON document of the form
    ``[[group_id, "0;x1,y1;x2,y2;..."], ...]`` where each group is a
    contiguous trajectory segment. We flatten the points across groups
    into the ``"x,y;x,y;..."`` shape that downstream consumers (the
    ``Map`` Rust helper in particular) already accept.

    Used in lieu of the legacy ``GetMapTrace`` fallback for these devices.
    """

    NAME = "onMapTrace"

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        """Handle message->body->data and notify the correct event subscribers."""
        info = data.get("info")
        if not info:
            # Not the compressed-envelope variant — leave to legacy GetMapTrace
            return HandlingResult.analyse()

        try:
            decompressed = decompress_base64_data(info)
            groups = orjson.loads(decompressed)
        except Exception:
            _LOGGER.debug("Could not decompress/parse onMapTrace info field")
            return HandlingResult.analyse()

        flat_points: list[str] = []
        for group in groups:
            # Each group: [group_id_str, "0;x1,y1;x2,y2;...;", "0;x,y;..." ...]
            if not isinstance(group, list):
                continue
            for segment in group[1:]:
                if not isinstance(segment, str):
                    continue
                # Drop the leading "0" anchor and any empty trailing segment
                pts = [p for p in segment.split(";") if p and p != "0"]
                flat_points.extend(pts)

        if not flat_points:
            return HandlingResult.analyse()

        # Use serial as a stable monotonic ``start`` so ``Map`` does not clear
        # the trace on every push — only the very first ever (serial == 0)
        # would trigger the reset, which is the firmware's intent.
        try:
            start = int(data.get("serial", 1))
        except (TypeError, ValueError):
            start = 1

        event_bus.notify(
            MapTraceEvent(start=start, total=start, data=";".join(flat_points))
        )
        return HandlingResult.success()
