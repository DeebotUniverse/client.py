from typing import Optional

import pytest

from deebot_client.map import _calc_point

_test_calc_point_data = [
    (0, 10, None, (0, 10)),
    (10, 100, (100, 0, 200, 50), (200, 50)),
    (10, 100, (0, 0, 1000, 1000), (400, 402)),
]


@pytest.mark.parametrize("x,y,image_box,expected", _test_calc_point_data)
def test_calc_point(
    x: int,
    y: int,
    image_box: Optional[tuple[int, int, int, int]],
    expected: tuple[int, int],
) -> None:
    result = _calc_point(x, y, image_box)
    assert result == expected
