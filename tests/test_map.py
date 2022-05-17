from typing import Optional

import pytest

from deebot_client.map import ImageBox

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
    box = ImageBox(image_box, False)
    result = box.calc_point(x, y)
    assert result == expected
