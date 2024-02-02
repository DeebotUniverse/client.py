from __future__ import annotations

import pycountry
import pytest

from deebot_client.util.continents import COUNTRIES_TO_CONTINENTS, get_continent


@pytest.mark.parametrize(
    ("continent", "expected"),
    [
        ("IT", "eu"),
        ("DE", "eu"),
        ("US", "na"),
        ("", "ww"),
        ("XX", "ww"),
    ],
)
def test_get_continent(continent: str, expected: str) -> None:
    assert get_continent(continent) == expected


def test_countries_list_match_pxycountries_one() -> None:
    expected_contires = {c.alpha_2 for c in pycountry.countries}

    assert set(COUNTRIES_TO_CONTINENTS.keys()) == expected_contires
