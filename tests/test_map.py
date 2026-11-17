from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast
from unittest.mock import ANY, AsyncMock, Mock, call, patch

import pytest

from deebot_client.events import RoomsEvent
from deebot_client.events.map import (
    CachedMapInfoEvent,
    Furniture,
    FurnitureEvent,
    MajorMapEvent,
    Map as MapInfo,
    MapChangedEvent,
    MapInfoEvent,
    MapSetEvent,
    MapSetType,
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
from deebot_client.models import Room
from deebot_client.rs.map import PositionType, RotationAngle
from tests import load_data_folder

from .common import block_till_done

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from _pytest.mark import ParameterSet
    from pytest_codspeed import BenchmarkFixture
    from syrupy.assertion import SnapshotAssertion

    from deebot_client.event_bus import EventBus
    from deebot_client.events.base import Event
    from deebot_client.models import StaticDeviceInfo


async def test_MapData(event_bus: EventBus) -> None:
    mock = AsyncMock()
    event_bus.subscribe(MapChangedEvent, mock)

    map_data = MapData(event_bus)

    async def test_cycle() -> None:
        positions = []
        for x in range(100):
            positions.append(Position(PositionType.DEEBOT, x, x, 0))
            map_data.update_positions(positions)

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

    calls = [
        call(MapSetEvent, ANY),
        call(MapSubsetEvent, ANY),
        call(MapInfoEvent, ANY),
        call(FurnitureEvent, ANY),
    ]
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
        RoomsEvent,
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

    exceptions = (
        ex.value.exceptions if isinstance(ex.value, ExceptionGroup) else [ex.value]
    )

    for err in exceptions:
        assert "Index out of bounds" in str(err)


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
        cast("Mock", map_obj._map_data.add_trace_points).assert_not_called()


def _changed(map_data: MapData) -> bool:
    """Return if the map data changed (as function, so mypy does not narrow it)."""
    return map_data.changed


async def test_rooms_and_furniture_mark_map_as_changed(
    execute_mock: AsyncMock,
    event_bus: EventBus,
    static_device_info: StaticDeviceInfo,
) -> None:
    """Test rooms and furniture are only taken over when they are different."""
    map_obj = await setup_map(execute_mock, event_bus, static_device_info)
    map_data = map_obj._map_data
    rooms = [Room("Kitchen", 1, "", center=(100, -200), neighbors=(2,))]
    furniture = [Furniture(id=0, type=20, coordinates="0,0,100,0,100,100")]

    events: list[tuple[Event, Event]] = [
        (RoomsEvent("1", rooms), RoomsEvent("1", list(rooms))),
        (FurnitureEvent("1", furniture), FurnitureEvent("1", list(furniture))),
    ]
    for event, same_data_event in events:
        map_data.reset_changed()
        event_bus.notify(event)
        await block_till_done(event_bus)
        assert map_data.changed

        # Same data again must not trigger a new image
        map_data.reset_changed()
        event_bus.notify(same_data_event)
        await block_till_done(event_bus)
        assert not map_data.changed

    assert map_data._rooms == {"1": rooms}
    assert map_data._furniture == {"1": furniture}


async def test_rooms_and_furniture_order_does_not_matter(
    execute_mock: AsyncMock,
    event_bus: EventBus,
    static_device_info: StaticDeviceInfo,
) -> None:
    """Test the same rooms and furniture in another order do not change the image."""
    map_obj = await setup_map(execute_mock, event_bus, static_device_info)
    map_data = map_obj._map_data
    kitchen = Room("Kitchen", 1, "", center=(100, -200))
    hall = Room("Hall", 2, "", center=(0, 0))
    carpet = Furniture(id=0, type=20, coordinates="0,0,100,0,100,100")
    bed = Furniture(id=1, type=8, coordinates="0,0,200,0,200,200")
    event_bus.notify(RoomsEvent("1", [hall, kitchen]))
    event_bus.notify(FurnitureEvent("1", [bed, carpet]))
    await block_till_done(event_bus)
    assert map_data._rooms == {"1": [kitchen, hall]}
    assert map_data._furniture == {"1": [carpet, bed]}

    map_data.reset_changed()
    event_bus.notify(RoomsEvent("1", [kitchen, hall]))
    event_bus.notify(FurnitureEvent("1", [carpet, bed]))
    await block_till_done(event_bus)
    assert not _changed(map_data)


def _cached_map_info(active_map_id: str | None) -> CachedMapInfoEvent:
    return CachedMapInfoEvent(
        {
            MapInfo(
                id=map_id,
                name=map_id,
                using=active_map_id is not None and map_id == active_map_id,
                built=True,
                angle=RotationAngle.DEG_0,
            )
            for map_id in ("1", "2")
        }
    )


async def test_rooms_and_furniture_of_other_maps_are_not_drawn(
    execute_mock: AsyncMock,
    event_bus: EventBus,
    static_device_info: StaticDeviceInfo,
) -> None:
    """Test only rooms and furniture of the active map are used."""
    map_obj = await setup_map(execute_mock, event_bus, static_device_info)
    map_data = map_obj._map_data
    rooms_1 = [Room("Kitchen", 1, "", center=(100, -200))]
    rooms_2 = [Room("Attic", 1, "", center=(0, 0))]
    furniture_2 = [Furniture(id=0, type=20, coordinates="0,0,100,0,100,100")]

    # Until the active map is known, the latest data is drawn
    event_bus.notify(RoomsEvent("2", rooms_2))
    await block_till_done(event_bus)
    assert map_data._drawn_map_id == "2"

    event_bus.notify(_cached_map_info("1"))
    event_bus.notify(RoomsEvent("1", rooms_1))
    await block_till_done(event_bus)
    assert map_data._drawn_map_id == "1"

    # Data of a map, which is not in use, is stored but does not change the image
    map_data.reset_changed()
    event_bus.notify(FurnitureEvent("2", furniture_2))
    event_bus.notify(RoomsEvent("2", []))
    await block_till_done(event_bus)
    assert not _changed(map_data)
    assert map_data._drawn_map_id == "1"
    assert map_data._rooms == {"1": rooms_1, "2": []}
    assert map_data._furniture == {"2": furniture_2}

    # Switching the map uses the data of the other map
    event_bus.notify(_cached_map_info("2"))
    await block_till_done(event_bus)
    assert _changed(map_data)
    assert map_data._drawn_map_id == "2"


async def test_latest_map_is_drawn_when_no_map_is_in_use(
    execute_mock: AsyncMock,
    event_bus: EventBus,
    static_device_info: StaticDeviceInfo,
) -> None:
    """Test the previous active map is not kept, when no map is in use anymore."""
    map_obj = await setup_map(execute_mock, event_bus, static_device_info)
    map_data = map_obj._map_data
    event_bus.notify(_cached_map_info("1"))
    event_bus.notify(RoomsEvent("1", [Room("Kitchen", 1, "", center=(100, -200))]))
    await block_till_done(event_bus)
    assert map_data._drawn_map_id == "1"

    event_bus.notify(_cached_map_info(None))
    await block_till_done(event_bus)

    map_data.reset_changed()
    event_bus.notify(RoomsEvent("2", [Room("Attic", 1, "", center=(0, 0))]))
    await block_till_done(event_bus)
    assert _changed(map_data)
    assert map_data._drawn_map_id == "2"


def _room_subset(room: Room) -> MapSubsetEvent:
    return MapSubsetEvent(
        id=room.id,
        type=MapSetType.ROOMS,
        coordinates=room.coordinates,
        name=room.name,
    )


async def test_removed_rooms_are_not_drawn(
    execute_mock: AsyncMock,
    event_bus: EventBus,
    static_device_info: StaticDeviceInfo,
) -> None:
    """Test rooms, which the bot does not report anymore, are removed."""
    map_obj = await setup_map(execute_mock, event_bus, static_device_info)
    map_data = map_obj._map_data
    kitchen = Room("Kitchen", 1, "0,0;100,0;100,100")
    hall = Room("Hall", 2, "200,0;300,0;300,100")
    event_bus.notify(MapSetEvent(MapSetType.ROOMS, [1, 2], "1"))
    event_bus.notify(_room_subset(kitchen))
    event_bus.notify(_room_subset(hall))
    await block_till_done(event_bus)
    assert map_data._rooms == {"1": [kitchen, hall]}

    # Nothing removed
    map_data.reset_changed()
    event_bus.notify(MapSetEvent(MapSetType.ROOMS, [2, 1], "1"))
    await block_till_done(event_bus)
    assert not _changed(map_data)
    assert map_data._rooms == {"1": [kitchen, hall]}

    event_bus.notify(MapSetEvent(MapSetType.ROOMS, [2], "1"))
    await block_till_done(event_bus)
    assert _changed(map_data)
    assert map_data._rooms == {"1": [hall]}

    # A removed room can be added again
    event_bus.notify(MapSetEvent(MapSetType.ROOMS, [1, 2], "1"))
    event_bus.notify(_room_subset(kitchen))
    await block_till_done(event_bus)
    assert map_data._rooms == {"1": [kitchen, hall]}

    map_data.reset_changed()
    event_bus.notify(MapSetEvent(MapSetType.ROOMS, [], "1"))
    await block_till_done(event_bus)
    assert _changed(map_data)
    assert map_data._rooms == {"1": []}


async def test_rooms_are_drawn_again_after_all_were_removed(
    execute_mock: AsyncMock,
    event_bus: EventBus,
    static_device_info: StaticDeviceInfo,
) -> None:
    """Test the same rooms as before are taken over, after the bot had no rooms."""
    map_obj = await setup_map(execute_mock, event_bus, static_device_info)
    map_data = map_obj._map_data
    rooms = [
        Room("Kitchen", 1, "", center=(100, -200)),
        Room("Hall", 2, "", center=(0, 0)),
    ]
    event_bus.notify(RoomsEvent("1", rooms))
    await block_till_done(event_bus)
    assert map_data._rooms == {"1": rooms}

    # Newer bots send all rooms at once and an empty list ends up as map set event
    event_bus.notify(MapSetEvent(MapSetType.ROOMS, [], "1"))
    await block_till_done(event_bus)
    assert map_data._rooms == {"1": []}

    event_bus.notify(RoomsEvent("1", list(rooms)))
    await block_till_done(event_bus)
    assert map_data._rooms == {"1": rooms}


async def test_rooms_removed_before_the_map_is_enabled_are_not_drawn(
    execute_mock: AsyncMock,
    event_bus: EventBus,
    static_device_info: StaticDeviceInfo,
) -> None:
    """Test the rooms event, which is sent on subscription, has no removed rooms."""

    async def on_change(_: MapChangedEvent) -> None:
        pass

    capabilities_map = static_device_info.capabilities.map
    assert capabilities_map is not None
    map_obj = Map(execute_mock, event_bus, capabilities_map)
    map_data = map_obj._map_data
    kitchen = Room("Kitchen", 1, "", center=(100, -200))
    hall = Room("Hall", 2, "", center=(0, 0))

    # The rooms are not known by the map yet, as nobody has asked for the image
    event_bus.notify(RoomsEvent("1", [kitchen, hall]))
    event_bus.notify(MapSetEvent(MapSetType.ROOMS, [], "1"))
    await block_till_done(event_bus)
    assert map_data._rooms == {}

    event_bus.subscribe(MapChangedEvent, on_change)
    await block_till_done(event_bus)
    assert map_data._rooms == {"1": []}


async def test_rooms_of_another_map_are_not_mixed(
    execute_mock: AsyncMock,
    event_bus: EventBus,
    static_device_info: StaticDeviceInfo,
) -> None:
    """Test the rooms of a map are not reported as rooms of another map."""
    map_obj = await setup_map(execute_mock, event_bus, static_device_info)
    map_data = map_obj._map_data
    kitchen = Room("Kitchen", 1, "0,0;100,0;100,100")
    hall = Room("Hall", 2, "200,0;300,0;300,100")
    attic = Room("Attic", 1, "0,0;500,0;500,500")
    event_bus.notify(MapSetEvent(MapSetType.ROOMS, [1, 2], "1"))
    event_bus.notify(_room_subset(kitchen))
    event_bus.notify(_room_subset(hall))
    await block_till_done(event_bus)

    # Same room id as the kitchen, but the room of the other map is not known yet
    event_bus.notify(MapSetEvent(MapSetType.ROOMS, [1], "2"))
    await block_till_done(event_bus)
    assert map_data._rooms == {"1": [kitchen, hall]}

    event_bus.notify(_room_subset(attic))
    await block_till_done(event_bus)
    assert map_data._rooms == {"1": [kitchen, hall], "2": [attic]}


def extractor_for_test_get_svg_map(module: ModuleType, filename: str) -> ParameterSet:
    """Extract EVENTS and SVG from the module."""
    required_attributes = ["EVENTS", "DEVICE_CLASS"]
    if not all(hasattr(module, attr) for attr in required_attributes):
        msg = f"Module does not have required attributes: {required_attributes}"
        raise AttributeError(msg)

    return pytest.param(
        module.DEVICE_CLASS,
        module.EVENTS,
        id=f"{filename}-{module.DEVICE_CLASS}",
    )


@pytest.mark.parametrize(
    ("device_class", "events"),
    load_data_folder("map", extractor_for_test_get_svg_map),
)
def test_get_svg_map(
    benchmark: BenchmarkFixture,
    snapshot: SnapshotAssertion,
    execute_mock: AsyncMock,
    event_bus: EventBus,
    static_device_info: StaticDeviceInfo,
    events: list[Event],
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

    assert svg_map == snapshot
