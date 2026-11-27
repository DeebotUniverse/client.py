"""Test rust functions."""

from __future__ import annotations

import base64
import lzma
from typing import TYPE_CHECKING

import pytest

from deebot_client.rs.util import (
    decompress_base64_data,
    parse_csv_ints,
    parse_csv_ints_via_float,
)

if TYPE_CHECKING:
    from pytest_codspeed import BenchmarkFixture


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "XQAABACZAAAAABaOQmW9Bsibxz42rKUpGlV7Rr4D1S/9x9mDa60v4J1BKrEsnk34EAt6X5gKkxwYzfOu3T8GAPpmIy5o4A==",
            b"-9125,3225;-9025,3225;-8975,3175;-8975,2475;-8925,2425;-8925,2375;-8325,2375;-8275,2425;-8225,2375;-8225,2425;-8174,2475;-8024,2475;-8024,4375;-9125,4375",
        ),
        (
            "XQAABABBAAAAAC2WwEIwUhHX3vfFDfs1H1PUqtdWgakwVnMBz3Bb3yaoE5OYkdYA",
            b'[["4","-6217","3919","-6217","231","-2642","231","-2642","3919"]]',
        ),
        (
            "XQAABADHAAAAAC2WwEHwYhHX3vWwDK80QCnaQU0mwUd9Vk34ub6OxzOk6kdFfbFvpVp4iIlKisAvp0MznQNYEZ8koxFHnO+iM44GUKgujGQKgzl0bScbQgaon1jI3eyCRikWlkmrbwA=",
            b'[["0","-5195","-1059","-5195","-37","-5806","-37","-5806","-1059"],["1","-7959","220","-7959","1083","-9254","1083","-9254","220"],["2","-9437","347","-5387","410"],["3","-5667","317","-4888","-56"]]',
        ),
        (
            "XQAABACvAAAAAAAAAEINQkt4BfqEvt9Pow7YU9KWRVBcSBosIDAOtACCicHy+vmfexxcutQUhqkAPQlBawOeXo/VSrOqF7yhdJ1JPICUs3IhIebU62Qego0vdk8oObiLh3VY/PVkqQyvR4dHxUDzMhX7HAguZVn3yC17+cQ18N4kaydN3LfSUtV/zejrBM4=",
            b'\x00\x00\x01\x00\x98\xf6\xff\x01\x00\x18\xf9\xff\xf8\xff@\x00\x00\xf1\xff@\x06\x00\xe9\xff@\x0b\x00\xe0\xff@\x15\x00\xe2\xff@\x1f\x00\xe2\xff@(\x00\xde\xff@.\x00\xd6\xff@5\x00\xcd\xff@4\x00\xc3\xff@0\x00\xba\xff@,\x00\xb1\xff@"\x00\xad\xff@\x18\x00\xad\xff@\x0e\x00\xae\xff@\x06\x00\xb4\xff@\x00\x00\xbc\xff@\xfe\xff\xc5\xff@\x00\x00\xd0\xff@\x03\x00\xda\xff@\x0b\x00\xe0\xff@\x15\x00\xe3\xff@\x15\x00\xed\xffH\x0e\x00\xf4\xffH\x05\x00\xf9\xffH\x0c\x00\xf2\xffH\x15\x00\xee\xffH\x1f\x00\xec\xffH)\x00\xec\xffH3\x00\xe8\xffH:\x00\xe1\xffH@\x00\xd9\xff@F\x00\xd1\xff@',
        ),
    ],
    ids=["1", "2", "3", "4"],
)
def test_decompress_base64_data_lzma(
    benchmark: BenchmarkFixture, value: str, expected: bytes
) -> None:
    """Test decompress_base64_data function with lzma base64 values."""
    # Benchmark only the production function
    result = benchmark(decompress_base64_data, value)
    assert result == expected

    # Verify that the old python function is producing the same result
    assert _decompress_7z_base64_data_python(value) == result


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "KLUv/SB//QEAMgQKDKClbQC+WNsvI/5vYPMSO6jz8h7OwN2BYlTHRR2DYgSeurlRRyp2UAgALXwANbAWWqAuACQBKiDgFiUJ",
            b"-624,-774;-524,-774;-474,-724;-424,-724;-374,-674;-124,-674;-24,-774;-74,-824;2325,-824;2375,-774;2425,-774;2425,1225;-624,1225",
        ),
    ],
    ids=["1"],
)
def test_decompress_base64_data_zstd(
    benchmark: BenchmarkFixture, value: str, expected: bytes
) -> None:
    """Test decompress_base64_data function with zstd base64 values."""
    # Benchmark only the production function
    result = benchmark(decompress_base64_data, value)
    assert result == expected


@pytest.mark.parametrize(
    ("value", "expected_error"),
    [
        (
            "XQAABADHAAAAAC2WwEHwYhHX3vWwDK80QCnaQU0mwUd9Vk34ub6OxzOk6kdFfbFvpVp4iIlKisAvp0MznQNYEZ8koxFHnO,+iM44GUKgujGQKgzl0bScbQgaon1jI3eyCRikWlkmrbwA=",
            "Invalid symbol 44, offset 94.",
        ),
        (
            "XQAABABBAAAAAC2WwEIwUhHX3vfFDfs1H1PUqtdWgakwVnMBz3Bb3yaoE5OYkd",
            "Invalid padding",
        ),
        (
            "AAABAA==",
            "Invalid 7z compressed data",
        ),
    ],
)
def test_decompress_base64_data_errors(value: str, expected_error: str) -> None:
    """Test decompress_base64_data function."""
    with pytest.raises(ValueError, match=expected_error):
        assert decompress_base64_data(value)


def _decompress_7z_base64_data_python(data: str) -> bytes:
    """Decompress base64 decoded 7z compressed string."""
    final_array = bytearray()

    # Decode Base64
    decoded = base64.b64decode(data)

    for i, idx in enumerate(decoded):
        if i == 8:
            final_array.extend(b"\x00\x00\x00\x00")
        final_array.append(idx)

    dec = lzma.LZMADecompressor(lzma.FORMAT_AUTO, None, None)
    return dec.decompress(final_array)


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
def test_parse_csv_ints_via_float(
    benchmark: BenchmarkFixture, value: str, expected: list[int]
) -> None:
    """Test that parse_csv_ints_via_float produces correct results."""
    result = benchmark(parse_csv_ints_via_float, value)
    assert result == expected

    # Verify Python baseline produces the same result
    python_result = _parse_csv_ints_via_float_python(value)
    assert result == python_result


def test_parse_csv_ints_via_float_errors() -> None:
    """Test that parse_csv_ints_via_float raises errors for invalid input."""
    with pytest.raises(ValueError, match="invalid float literal"):
        parse_csv_ints_via_float("1,2,invalid,3")
