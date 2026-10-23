"""Native map commands (Y1 Pro opcodes 30001 and 30004)."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from deebot_client.command import InitParam
from deebot_client.events import CachedMapInfoEvent
from deebot_client.events.map import NativeMapRefreshEvent
from deebot_client.logging_filter import get_logger
from deebot_client.map_ids import valid_mid
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.messages.json.native_map import parse_native_map_data

from .common import JsonCommandMqttP2P
from .native_common import NativeExecuteCommand, NativeGetCommand

if TYPE_CHECKING:
    from collections.abc import Sequence

    from deebot_client.event_bus import EventBus

_LOGGER = get_logger(__name__)


def _validate_map_id(map_id: str) -> str:
    if not map_id or not map_id.strip() or map_id.strip() == "0":
        msg = "map_id must be a non-empty string"
        raise ValueError(msg)
    return map_id.strip()


def _with_request_context(response: dict[str, Any], map_id: str) -> dict[str, Any]:
    """Copy envelope, defaulting missing outer mapId to requesting id."""
    resp = response.get("resp")
    if not isinstance(resp, dict):
        return response
    body = resp.get("body")
    if not isinstance(body, dict):
        return response
    data = body.get("data")
    if not isinstance(data, dict):
        return response
    if valid_mid(data.get("mapId")) is not None:
        return response
    return {
        **response,
        "resp": {**resp, "body": {**body, "data": {**data, "mapId": map_id}}},
    }


class GetNativeMapData(NativeGetCommand):
    """Get native map data command (opcode 30001).

    Push path uses opcode 30000. Getter needs no MQTT P2P; missing outer
    reply mapId is associated from requesting map_id on a copied payload.
    """

    NAME = "30001"

    def __init__(self, fields: Sequence[str], map_id: str | None = None) -> None:
        if not fields:
            msg = "fields must be a non-empty sequence"
            raise ValueError(msg)
        self.fields = list(fields)
        self.map_id = _validate_map_id(map_id) if map_id is not None else None

        args: dict[str, Any] = {"fields": self.fields}
        if self.map_id is not None:
            args["mapId"] = self.map_id

        super().__init__(args)

    @classmethod
    def get_catalog(cls) -> GetNativeMapData:
        """Create query for saved map catalog."""
        return cls(["mapInfos"])

    @classmethod
    def get_status(cls) -> GetNativeMapData:
        """Create query for map progress status."""
        return cls(["mapStatus"])

    @classmethod
    def get_map(cls, map_id: str) -> GetNativeMapData:
        """Create query for map raster, rooms, and dock position."""
        return cls(["mapData", "areas", "pos"], map_id)

    @classmethod
    def get_traces(cls, map_id: str) -> GetNativeMapData:
        """Create query for cleaning trajectory."""
        return cls(["mapTraceData"], map_id)

    @classmethod
    def get_overlays(cls, map_id: str) -> GetNativeMapData:
        """Create query for virtual walls and restricted zones."""
        return cls(["virtualWalls", "mopWalls", "carpets"], map_id)

    @classmethod
    def _handle_body_data_dict(
        cls, event_bus: EventBus, data: dict[str, Any]
    ) -> HandlingResult:
        return parse_native_map_data(event_bus, data)

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> HandlingResult:
        prepared = response
        if self.map_id is not None:
            prepared = _with_request_context(response, self.map_id)
        result = super()._handle_response(event_bus, prepared)
        if (
            result.state == HandlingState.SUCCESS
            and result.args
            and "map_id" in result.args
            and event_bus.capabilities.map
        ):
            active_mid = result.args["map_id"]
            result.requested_commands.extend(
                [
                    GetNativeMapData.get_map(active_mid),
                    GetNativeMapData.get_traces(active_mid),
                    GetNativeMapData.get_overlays(active_mid),
                ]
            )
        return result


class NativeMapSwitch(NativeExecuteCommand, JsonCommandMqttP2P):
    """Switch active navigation map (opcode 30004)."""

    NAME = "30004"
    _mqtt_params = MappingProxyType(
        {"mapId": InitParam(str, "map_id"), "request": None}
    )

    def __init__(self, map_id: str) -> None:
        valid_map_id = _validate_map_id(map_id)
        self.map_id = valid_map_id
        super().__init__({"mapId": valid_map_id, "request": "mapSwitch"})

    def _handle_response(
        self, event_bus: EventBus, response: dict[str, Any]
    ) -> HandlingResult:
        result = super()._handle_response(event_bus, response)
        if (
            result.state == HandlingState.SUCCESS
            and event_bus.capabilities.map
            and event_bus.capabilities.map.map_switch is not None
        ):
            result.requested_commands.extend(
                [
                    GetNativeMapData.get_catalog(),
                    GetNativeMapData.get_map(self.map_id),
                    GetNativeMapData.get_traces(self.map_id),
                    GetNativeMapData.get_overlays(self.map_id),
                ]
            )
        return result

    def _handle_mqtt_p2p(self, event_bus: EventBus, response: dict[str, Any]) -> None:
        result = self.handle(event_bus, response)
        if result.state == HandlingState.SUCCESS:
            event_bus.request_refresh(CachedMapInfoEvent)
            event_bus.notify(NativeMapRefreshEvent(self.map_id))
