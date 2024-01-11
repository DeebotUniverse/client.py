import pytest

from deebot_client.util.continents import get_continent


@pytest.mark.parametrize(
    ("continent", "expected"),
    [
        ("it", "eu"),
        ("de", "eu"),
        ("us", "na"),
        ("invalid", "ww"),
        ("", "ww"),
        ("xx", "ww"),
    ],
)
def test_get_continent(continent: str, expected: str) -> None:
    assert get_continent(continent) == expected
