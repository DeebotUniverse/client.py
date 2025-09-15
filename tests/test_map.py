from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import ANY, AsyncMock, Mock, call, patch

import pytest

from deebot_client.events.map import (
    CachedMapInfoEvent,
    MajorMapEvent,
    MapChangedEvent,
    MapSetEvent,
    MapSubsetEvent,
    MapTraceEvent,
    MinorMapEvent,
    Position,
    PositionsEvent,
)
from deebot_client.map import (
    Map,
    MapData,
)
from deebot_client.models import Room, StaticDeviceInfo
from deebot_client.rs.map import PositionType
from tests import load_data_folder

from .common import block_till_done

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from _pytest.mark import ParameterSet
    from pytest_codspeed import BenchmarkFixture

    from deebot_client.event_bus import EventBus
    from deebot_client.events.base import Event


async def test_MapData(event_bus: EventBus) -> None:
    mock = AsyncMock()
    event_bus.subscribe(MapChangedEvent, mock)

    map_data = MapData(event_bus)

    async def test_cycle() -> None:
        positions = []
        for x in range(100):
            positions.append(Position(PositionType.DEEBOT, x, x, 0))
            map_data.update_positions(positions)
            map_data.rooms[x] = Room("test", x, "1,2")

        assert map_data.changed is True
        mock.assert_called_once()

        await asyncio.sleep(1.1)
        assert mock.call_count == 2

    await test_cycle()

    mock.reset_mock()
    map_data.reset_changed()
    await asyncio.sleep(1.1)

    await test_cycle()


def _test_Map_subscriptions_subscribe(event_bus_mock: Mock) -> None:
    async def on_cached_info(_: CachedMapInfoEvent) -> None:
        pass

    event_bus_mock.subscribe(CachedMapInfoEvent, on_cached_info)
    event_bus_mock.subscribe.reset_mock()


@pytest.mark.parametrize(
    ("prepare_fn", "events_with_subscriber"),
    [(lambda _: None, []), (_test_Map_subscriptions_subscribe, [CachedMapInfoEvent])],
    ids=["No CachedMapInfoEvent subscribers", "Already CachedMapInfoEvent subscribers"],
)
async def test_Map_subscriptions(
    execute_mock: AsyncMock,
    event_bus_mock: Mock,
    event_bus: EventBus,
    prepare_fn: Callable[[Mock], None],
    events_with_subscriber: list[type[Event]],
    static_device_info: StaticDeviceInfo,
) -> None:
    prepare_fn(event_bus_mock)
    capabilities_map = static_device_info.capabilities.map
    assert capabilities_map is not None
    map_obj = Map(execute_mock, event_bus_mock, capabilities_map)

    calls = [call(MapSetEvent, ANY), call(MapSubsetEvent, ANY)]
    event_bus_mock.subscribe.assert_has_calls(calls)
    event_bus_mock.add_on_subscription_callback.assert_called_once_with(
        MapChangedEvent, ANY
    )
    # +1 is for the on_first_subscription call
    num_unsubs = len(calls) + 1
    assert len(map_obj._unsubscribers) == num_unsubs

    async def on_change() -> None:
        pass

    event_unsub = event_bus_mock.subscribe(MapChangedEvent, on_change)
    await block_till_done(event_bus)

    events = [
        MajorMapEvent,
        MinorMapEvent,
        CachedMapInfoEvent,
        PositionsEvent,
        MapTraceEvent,
    ]

    calls.append(call(MapChangedEvent, on_change))
    calls.extend([call(event, ANY) for event in events])
    event_bus_mock.subscribe.assert_has_calls(calls)
    assert len(map_obj._unsubscribers) == num_unsubs
    for event in events:
        assert event_bus.has_subscribers(event)

    event_unsub()
    for event in events:
        if event not in events_with_subscriber:
            assert not event_bus.has_subscribers(event)

    await map_obj.teardown()
    assert not map_obj._unsubscribers


async def setup_map(
    execute_mock: AsyncMock, event_bus: EventBus, static_device_info: StaticDeviceInfo
) -> Map:
    async def on_change(_: MapChangedEvent) -> None:
        pass

    capabilities_map = static_device_info.capabilities.map
    assert capabilities_map is not None
    map_obj = Map(execute_mock, event_bus, capabilities_map)
    event_bus.subscribe(MapChangedEvent, on_change)
    await block_till_done(event_bus)
    return map_obj


@pytest.mark.parametrize(
    ("event", "exception_class"),
    [
        (MinorMapEvent(65, "data"), ValueError),
        (
            MajorMapEvent(
                map_id="1132127808",
                values=[1295764014 for _ in range(100)],
                requested=True,
            ),
            ExceptionGroup,
        ),
    ],
    ids=["MinorMapEvent", "MajorMapEvent"],
)
async def test_invalid_map_piece_index(
    execute_mock: AsyncMock,
    event_bus: EventBus,
    event: Event,
    exception_class: type[Exception],
    static_device_info: StaticDeviceInfo,
) -> None:
    """Test invalid map piece index."""
    await setup_map(execute_mock, event_bus, static_device_info)

    event_bus.notify(event)
    with pytest.raises(exception_class) as ex:
        await block_till_done(event_bus)

    exceptions = ex.value.exceptions if isinstance(ex.value, ExceptionGroup) else [ex]

    for ex in exceptions:
        assert "Index out of bounds" in str(ex)


async def test_get_svg_map_empty(
    execute_mock: AsyncMock,
    event_bus: EventBus,
    static_device_info: StaticDeviceInfo,
) -> None:
    """Test getting svg map without data returns None."""
    map_obj = await setup_map(execute_mock, event_bus, static_device_info)
    assert map_obj.get_svg_map() is None


async def test_empty_maptrace(
    execute_mock: AsyncMock,
    event_bus: EventBus,
    static_device_info: StaticDeviceInfo,
) -> None:
    """Test empty data will not raise exception."""
    with patch("deebot_client.map.MapData", autospec=True):
        map_obj = await setup_map(execute_mock, event_bus, static_device_info)
        event_bus.notify(MapTraceEvent(0, 0, ""))
        await block_till_done(event_bus)
        map_obj._map_data.add_trace_points.assert_not_called()


def extractor_for_test_get_svg_map(module: ModuleType, filename: str) -> ParameterSet:
    """Extract EVENTS and SVG from the module."""
    required_attributes = ["EVENTS", "SVG", "DEVICE_CLASS"]
    if not all(hasattr(module, attr) for attr in required_attributes):
        msg = f"Module does not have required attributes: {required_attributes}"
        raise AttributeError(msg)

    # To keep codspeed test history, we hide the params for the original test, which is now test_1
    test_name = (
        pytest.HIDDEN_PARAM
        if filename == "test_1"
        else f"{filename}-{module.DEVICE_CLASS}"
    )

    return pytest.param(
        module.DEVICE_CLASS,
        module.EVENTS,
        module.SVG,
        id=test_name,
    )


@pytest.mark.parametrize(
    ("device_class", "events", "expected_svg"),
    load_data_folder("map", extractor_for_test_get_svg_map),
)
def test_get_svg_map(
    benchmark: BenchmarkFixture,
    execute_mock: AsyncMock,
    event_bus: EventBus,
    static_device_info: StaticDeviceInfo,
    events: list[Event],
    expected_svg: str,
) -> None:
    """Test getting svg map."""
    event_loop = asyncio.new_event_loop()

    async def test_fn() -> str | None:
        map_obj = await setup_map(execute_mock, event_bus, static_device_info)

        for event in events:
            event_bus.notify(event)

        await block_till_done(event_bus)
        return map_obj.get_svg_map()

    @benchmark
    def svg_map() -> str | None:
        return event_loop.run_until_complete(test_fn())

    assert svg_map == expected_svg
