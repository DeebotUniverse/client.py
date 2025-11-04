"""Test and benchmark Rust string parsing functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.rs.util import parse_csv_ints, parse_csv_ints_via_float

if TYPE_CHECKING:
    from pytest_codspeed import BenchmarkFixture


# Python baseline implementations for comparison
def _parse_csv_ints_python(value: str) -> list[int]:
    """Python baseline: parse comma-separated integers."""
    return [int(x) for x in value.split(",") if x]


def _parse_csv_ints_via_float_python(value: str) -> list[int]:
    """Python baseline: parse comma-separated floats and convert to ints."""
    return [int(float(x)) for x in value.split(",") if x]


# Edge cases
EMPTY_DATA = ""
TRAILING_COMMAS = "1,2,3,,"
WHITESPACE_DATA = " 1 , 2 , 3 "
REAL_DATA_INTS = [
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    817288174,
    3571566673,
    2120918229,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    4119863044,
    3345372489,
    1125149782,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    2826859129,
    3628293953,
    1436915986,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    3857336909,
    2692517274,
    3424129059,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    1295764014,
    2514771601,
    2675258590,
    3347634930,
    1295764014,
    1295764014,
    1295764014,
]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (",".join(str(x) for x in REAL_DATA_INTS), REAL_DATA_INTS),
        (EMPTY_DATA, []),
        (TRAILING_COMMAS, [1, 2, 3]),
        (WHITESPACE_DATA, [1, 2, 3]),
        ("123", [123]),
        ("-1,-2,-3", [-1, -2, -3]),
    ],
    ids=["real data", "empty", "trailing_commas", "whitespace", "single", "negative"],
)
def test_parse_csv_ints(
    benchmark: BenchmarkFixture, value: str, expected: list[int]
) -> None:
    """Test that parse_csv_ints produces correct results."""
    result = benchmark(parse_csv_ints, value)
    assert result == expected

    # Verify Python baseline produces the same result
    python_result = _parse_csv_ints_python(value)
    assert result == python_result


@pytest.mark.parametrize(
    "value",
    [
        "1,2,a,3",  # Invalid integer
        "1.5,2.5",  # Floats (not supported in direct int parsing)
    ],
    ids=["invalid_int", "float_values"],
)
def test_parse_csv_ints_errors(value: str) -> None:
    """Test that parse_csv_ints raises errors for invalid input."""
    with pytest.raises(ValueError, match="invalid digit found in string"):
        parse_csv_ints(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("-606.000000,11191.000000,2824.000000,8497.000000", [-606, 11191, 2824, 8497]),
        (EMPTY_DATA, []),
        (TRAILING_COMMAS, [1, 2, 3]),
        (WHITESPACE_DATA, [1, 2, 3]),
        ("123.456", [123]),
        ("-1.5,-2.7,-3.9", [-1, -2, -3]),
    ],
    ids=[
        "real data",
        "empty",
        "trailing_commas",
        "whitespace",
        "single",
        "negative",
    ],
)
def test_parse_csv_ints_via_float_correctness(value: str, expected: list[int]) -> None:
    """Test that parse_csv_ints_via_float produces correct results."""
    result = parse_csv_ints_via_float(value)
    assert result == expected

    # Verify Python baseline produces the same result
    python_result = _parse_csv_ints_via_float_python(value)
    assert result == python_result


def test_parse_csv_ints_via_float_errors() -> None:
    """Test that parse_csv_ints_via_float raises errors for invalid input."""
    with pytest.raises(ValueError, match="invalid float literal"):
        parse_csv_ints_via_float("1,2,invalid,3")
