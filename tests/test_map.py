import asyncio
from unittest.mock import ANY, AsyncMock, Mock, call

import pytest

from deebot_client.event_bus import EventBus
from deebot_client.events.map import (
    MapChangedEvent,
    MapSetEvent,
    MapSubsetEvent,
    Position,
    PositionType,
)
from deebot_client.map import Map, MapData, _calc_point
from deebot_client.models import Room

_test_calc_point_data = [
    (0, 10, None, (0, 10)),
    (10, 100, (100, 0, 200, 50), (200, 50)),
    (10, 100, (0, 0, 1000, 1000), (400, 402)),
]


@pytest.mark.parametrize(("x", "y", "image_box", "expected"), _test_calc_point_data)
def test_calc_point(
    x: int,
    y: int,
    image_box: tuple[int, int, int, int] | None,
    expected: tuple[int, int],
) -> None:
    result = _calc_point(x, y, image_box)
    assert result == expected


async def test_MapData(event_bus: EventBus) -> None:
    mock = AsyncMock()
    event_bus.subscribe(MapChangedEvent, mock)

    map_data = MapData(event_bus)

    async def test_cycle() -> None:
        for x in range(10000):
            map_data.positions.append(Position(PositionType.DEEBOT, x, x))
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


async def test_Map_internal_subscriptions(
    execute_mock: AsyncMock, event_bus_mock: Mock
) -> None:
    map = Map(execute_mock, event_bus_mock)

    calls = [call(MapSetEvent, ANY), call(MapSubsetEvent, ANY)]
    event_bus_mock.subscribe.assert_has_calls(calls)
    assert len(map._unsubscribers_internal) == len(calls)

    await map.teardown()
    assert not map._unsubscribers_internal
