from time import sleep
from unittest.mock import Mock

import pytest

from deebot_client.events.map import MapChangedEvent, Position, PositionType
from deebot_client.map import MapData, _calc_point
from deebot_client.models import Room

_test_calc_point_data = [
    (0, 10, None, (0, 10)),
    (10, 100, (100, 0, 200, 50), (200, 50)),
    (10, 100, (0, 0, 1000, 1000), (400, 402)),
]


@pytest.mark.parametrize("x,y,image_box,expected", _test_calc_point_data)
def test_calc_point(
    x: int,
    y: int,
    image_box: tuple[int, int, int, int] | None,
    expected: tuple[int, int],
) -> None:
    result = _calc_point(x, y, image_box)
    assert result == expected


def test_MapData() -> None:
    last_event: MapChangedEvent | None = None

    def get_last_event(_: type[MapChangedEvent]) -> MapChangedEvent | None:
        nonlocal last_event
        return last_event

    def notify(event: MapChangedEvent) -> None:
        nonlocal last_event
        last_event = event

    event_bus = Mock()
    event_bus.get_last_event.side_effect = get_last_event
    event_bus.notify.side_effect = notify

    map_data = MapData(event_bus)

    def test_cycle() -> None:
        for x in range(4):
            map_data.positions.append(Position(PositionType.DEEBOT, x, x))
            map_data.rooms[x] = Room("test", x, "1,2")

        assert event_bus.notify.call_count == 1

    test_cycle()

    event_bus.reset_mock()
    sleep(1.1)

    test_cycle()
