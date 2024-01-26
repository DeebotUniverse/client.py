from __future__ import annotations

import pytest

from deebot_client.util.continents import get_continent


@pytest.mark.parametrize(
    ("continent", "expected"),
    [
        ("IT", "eu"),
        ("it", "eu"),
        ("DE", "eu"),
        ("US", "na"),
        ("invalid", "ww"),
        ("", "ww"),
        ("XX", "ww"),
    ],
)
def test_get_continent(continent: str, expected: str) -> None:
    assert get_continent(continent) == expected
