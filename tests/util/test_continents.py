import pytest

from deebot_client.util.continents import get_continent


@pytest.mark.parametrize(
    ("continent", "expected"),
    [
        ("IT", "EU"),
        ("DE", "EU"),
        ("US", "NA"),
        ("invalid", "WW"),
        ("", "WW"),
        ("XX", "WW"),
    ],
)
def test_get_continent(continent: str, expected: str) -> None:
    assert get_continent(continent) == expected
