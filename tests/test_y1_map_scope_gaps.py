from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import orjson
import pytest

from deebot_client.commands.json.native_map import GetNativeMapData
from deebot_client.event_bus import EventBus
from deebot_client.events import (
    CachedMapInfoEvent,
    Event,
    MapChangedEvent,
    MapSetType,
    MapSubsetEvent,
    NativeTraceEvent,
    PositionsEvent,
    RoomsEvent,
)
from deebot_client.events.map import Map as SavedMap
from deebot_client.hardware.cqyi87 import get_device_info
from deebot_client.map import Map
from deebot_client.messages.json.native_map import parse_native_map_data
from deebot_client.rs.map import RotationAngle
from tests.common import block_till_done

if TYPE_CHECKING:
    from deebot_client.models import DeviceInfo, StaticDeviceInfo

from tests.commands.json.test_native_mqtt_roundtrip import (
    _request_topic,
    _response_topic,
    _subscribed_client,
)


async def test_advertised_trace_subscription_receives_native_report() -> None:
    caps = get_device_info().capabilities
    assert caps.map is not None
    bus = EventBus(AsyncMock(return_value={}), caps)
    received: list[Event] = []

    async def receive(event: Event) -> None:
        received.append(event)

    bus.subscribe(caps.map.trace.event, receive)
    try:
        parse_native_map_data(
            bus,
            {
                "mapId": "synthetic-map",
                "mapTraceData": {
                    "traceId": 17,
                    "start": 0,
                    "totalCount": 2,
                    "lz4Len": 8,
                    "trace": "UAoAFAAA",
                },
            },
        )
        await block_till_done(bus)
        assert len(received) == 1
        assert isinstance(received[0], NativeTraceEvent)
    finally:
        await bus.teardown()


@pytest.mark.parametrize("event_type", [PositionsEvent, RoomsEvent, NativeTraceEvent])
async def test_standalone_map_subscription_requests_initial_data(
    event_type: type[Event],
) -> None:
    execute = AsyncMock(return_value={})
    bus = EventBus(execute, get_device_info().capabilities)

    async def receive(_: Event) -> None:
        return

    bus.subscribe(event_type, receive)
    try:
        await block_till_done(bus)
        assert execute.await_count > 0
        assert all(call.args[0].NAME == "30001" for call in execute.await_args_list)
    finally:
        await bus.teardown()


async def test_legacy_map_subsets_keep_integer_keys(
    event_bus: EventBus,
    static_device_info: StaticDeviceInfo,
    execute_mock: AsyncMock,
) -> None:
    caps = static_device_info.capabilities.map
    assert caps is not None
    model = Map(execute_mock, event_bus, caps)
    subset = MapSubsetEvent(7, MapSetType.VIRTUAL_WALLS, "0,0,100,100")
    try:
        event_bus.notify(subset)
        await block_till_done(event_bus)
        assert model._map_data.map_subsets[7] == subset
    finally:
        await model.teardown()


@pytest.mark.parametrize("angle", [RotationAngle.DEG_180, RotationAngle.DEG_270])
async def test_inspected_rotation_updates_when_catalog_arrives_late(
    angle: RotationAngle,
) -> None:
    caps = get_device_info().capabilities
    assert caps.map is not None
    execute = AsyncMock(return_value={})
    bus = EventBus(execute, caps)
    model = Map(execute, bus, caps.map)

    async def receive(_: MapChangedEvent) -> None:
        return

    bus.subscribe(MapChangedEvent, receive)
    try:
        await block_till_done(bus)
        model.select_map("synthetic-inspected")
        bus.notify(
            CachedMapInfoEvent(
                {
                    SavedMap(
                        "synthetic-active", "Active", True, True, RotationAngle.DEG_90
                    ),
                    SavedMap(
                        "synthetic-inspected",
                        "Inspected",
                        False,
                        True,
                        angle,
                    ),
                }
            )
        )
        await block_till_done(bus)
        assert model._map_data._rotation == angle
    finally:
        await model.teardown()
        await bus.teardown()


async def test_native_overlay_types_with_same_id_both_render() -> None:
    caps = get_device_info().capabilities
    assert caps.map is not None
    execute = AsyncMock(return_value={})
    bus = EventBus(execute, caps)
    model = Map(execute, bus, caps.map)

    async def receive(_: MapChangedEvent) -> None:
        return

    bus.subscribe(MapChangedEvent, receive)
    try:
        await block_till_done(bus)
        model.select_map("synthetic-overlay")
        parse_native_map_data(
            bus,
            {
                "mapId": "synthetic-overlay",
                "mapData": {
                    "width": 2,
                    "height": 2,
                    "xMin": 400,
                    "yMax": 401,
                    "resolution": 5,
                    "map": "QAAAAAA=",
                },
                "virtualWalls": "7,1,0,0,100,100",
                "mopWalls": "7,2,0,0,0,100,100,100,100,0",
            },
        )
        await block_till_done(bus)
        svg = model.get_svg_map()
        assert svg is not None
        assert '<path class="v"' in svg
        assert '<path class="m"' in svg
    finally:
        await model.teardown()
        await bus.teardown()


@pytest.mark.parametrize("code", [0, 500])
async def test_repeated_mqtt_edits_refresh_inspected_map(
    device_info: DeviceInfo, code: int
) -> None:
    caps = get_device_info().capabilities
    assert caps.map is not None
    execute = AsyncMock(return_value={})
    bus = EventBus(execute, caps)
    model = Map(execute, bus, caps.map)
    model.select_map("synthetic-inactive")
    client = _subscribed_client(device_info, bus)
    try:
        for request_id in ("synthetic-first", "synthetic-second"):
            client._handle_p2p(
                _request_topic("50009", device_info, request_id).split("/"),
                orjson.dumps(
                    {
                        "body": {
                            "data": {
                                "mapId": "synthetic-inactive",
                                "roomId": 7,
                                "name": "Synthetic room",
                            }
                        }
                    }
                ),
            )
            client._handle_p2p(
                _response_topic("50009", device_info, request_id).split("/"),
                orjson.dumps({"body": {"code": code}}),
            )
            await block_till_done(bus)
        assert execute.await_count == (6 if code == 0 else 0)
        for call in execute.await_args_list:
            command = call.args[0]
            assert isinstance(command, GetNativeMapData)
            assert command.map_id == "synthetic-inactive"
    finally:
        await model.teardown()
        await bus.teardown()
