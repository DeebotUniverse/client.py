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


# Test data representing realistic usage patterns
SMALL_DATA = "1,2,3,4,5"  # 5 values
MEDIUM_DATA = ",".join(str(i) for i in range(50))  # 50 values
LARGE_DATA = ",".join(str(i) for i in range(200))  # 200 values (realistic for stats)

SMALL_FLOAT_DATA = "1.5,2.7,3.1,4.9,5.2"  # 5 values
MEDIUM_FLOAT_DATA = ",".join(f"{i}.{i % 10}" for i in range(50))  # 50 values
LARGE_FLOAT_DATA = ",".join(f"{i}.{i % 10}" for i in range(200))  # 200 values

# Edge cases
EMPTY_DATA = ""
TRAILING_COMMAS = "1,2,3,,"
WHITESPACE_DATA = " 1 , 2 , 3 "


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (SMALL_DATA, [1, 2, 3, 4, 5]),
        (EMPTY_DATA, []),
        (TRAILING_COMMAS, [1, 2, 3]),
        (WHITESPACE_DATA, [1, 2, 3]),
        ("123", [123]),
        ("-1,-2,-3", [-1, -2, -3]),
    ],
    ids=["small", "empty", "trailing_commas", "whitespace", "single", "negative"],
)
def test_parse_csv_ints_correctness(value: str, expected: list[int]) -> None:
    """Test that parse_csv_ints produces correct results."""
    result = parse_csv_ints(value)
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
        (SMALL_FLOAT_DATA, [1, 2, 3, 4, 5]),
        ("1.9,2.1,3.5", [1, 2, 3]),
        (EMPTY_DATA, []),
        (TRAILING_COMMAS, [1, 2, 3]),
        (WHITESPACE_DATA, [1, 2, 3]),
        ("123.456", [123]),
        ("-1.5,-2.7,-3.9", [-1, -2, -3]),
    ],
    ids=[
        "small_float",
        "float_truncation",
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


# Benchmarks for parse_csv_ints
@pytest.mark.parametrize(
    "data",
    [SMALL_DATA, MEDIUM_DATA, LARGE_DATA],
    ids=["small_5_values", "medium_50_values", "large_200_values"],
)
def test_parse_csv_ints_rust(benchmark: BenchmarkFixture, data: str) -> None:
    """Benchmark Rust implementation of parse_csv_ints."""
    result = benchmark(parse_csv_ints, data)
    assert len(result) > 0

    # Verify Python baseline produces the same result
    python_result = _parse_csv_ints_python(data)
    assert result == python_result


@pytest.mark.parametrize(
    "data",
    [SMALL_DATA, MEDIUM_DATA, LARGE_DATA],
    ids=["small_5_values", "medium_50_values", "large_200_values"],
)
def test_parse_csv_ints_python(benchmark: BenchmarkFixture, data: str) -> None:
    """Benchmark Python baseline implementation of parse_csv_ints."""
    result = benchmark(_parse_csv_ints_python, data)
    assert len(result) > 0


# Benchmarks for parse_csv_ints_via_float
@pytest.mark.parametrize(
    "data",
    [SMALL_FLOAT_DATA, MEDIUM_FLOAT_DATA, LARGE_FLOAT_DATA],
    ids=["small_5_values", "medium_50_values", "large_200_values"],
)
def test_parse_csv_ints_via_float_rust(benchmark: BenchmarkFixture, data: str) -> None:
    """Benchmark Rust implementation of parse_csv_ints_via_float."""
    result = benchmark(parse_csv_ints_via_float, data)
    assert len(result) > 0

    # Verify Python baseline produces the same result
    python_result = _parse_csv_ints_via_float_python(data)
    assert result == python_result


@pytest.mark.parametrize(
    "data",
    [SMALL_FLOAT_DATA, MEDIUM_FLOAT_DATA, LARGE_FLOAT_DATA],
    ids=["small_5_values", "medium_50_values", "large_200_values"],
)
def test_parse_csv_ints_via_float_python(
    benchmark: BenchmarkFixture, data: str
) -> None:
    """Benchmark Python baseline implementation of parse_csv_ints_via_float."""
    result = benchmark(_parse_csv_ints_via_float_python, data)
    assert len(result) > 0


# Real-world usage benchmarks based on actual message patterns
def test_stats_content_realistic(benchmark: BenchmarkFixture) -> None:
    """Benchmark stats content parsing with realistic data.

    Based on actual ReportStats messages which contain area, time, and other
    cleaning statistics as comma-separated values.
    """
    # Realistic stats data: ~30-50 values typical for cleaning stats
    realistic_stats = ",".join(str(i * 10) for i in range(40))
    result = benchmark(parse_csv_ints_via_float, realistic_stats)
    assert len(result) == 40

    # Verify Python baseline produces the same result
    python_result = _parse_csv_ints_via_float_python(realistic_stats)
    assert result == python_result


def test_stats_content_realistic_python(benchmark: BenchmarkFixture) -> None:
    """Benchmark stats content parsing (Python baseline) with realistic data."""
    realistic_stats = ",".join(str(i * 10) for i in range(40))
    result = benchmark(_parse_csv_ints_via_float_python, realistic_stats)
    assert len(result) == 40


def test_map_crc_values(benchmark: BenchmarkFixture) -> None:
    """Benchmark map CRC value parsing.

    Based on OnMajorMap messages which contain 64 CRC32 checksums
    (one per map piece).
    """
    # Realistic map CRC data: 64 CRC32 values
    map_crcs = ",".join(str(1000000 + i * 12345) for i in range(64))
    result = benchmark(parse_csv_ints, map_crcs)
    assert len(result) == 64

    # Verify Python baseline produces the same result
    python_result = _parse_csv_ints_python(map_crcs)
    assert result == python_result


def test_map_crc_values_python(benchmark: BenchmarkFixture) -> None:
    """Benchmark map CRC value parsing (Python baseline)."""
    map_crcs = ",".join(str(1000000 + i * 12345) for i in range(64))
    result = benchmark(_parse_csv_ints_python, map_crcs)
    assert len(result) == 64
