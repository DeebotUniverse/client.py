from __future__ import annotations

import pytest

from deebot_client.util.countries import get_ecovacs_country


@pytest.mark.parametrize(
    ("continent", "expected"),
    [
        ("IT", "IT"),
        ("GB", "UK"),
    ],
)
def test_get_ecovacs_country(continent: str, expected: str) -> None:
    assert get_ecovacs_country(continent) == expected
