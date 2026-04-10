"""Test rust functions."""

from __future__ import annotations

import base64
import hashlib
import lzma
from typing import TYPE_CHECKING

import pytest

from deebot_client.rs.util import (
    decompress_base64_data,
    decompress_base64_lz4_data,
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
            b"\x00\x00\x01\x00\x98\xf6\xff\x01\x00\x18\xf9\xff\xf8\xff@\x00\x00\xf1\xff@\x06\x00\xe9\xff@\x0b\x00\xe0\xff@\x15\x00\xe2\xff@\x1f\x00\xe2\xff@(\x00\xde\xff@.\x00\xd6\xff@5\x00\xcd\xff@4\x00\xc3\xff@0\x00\xba\xff@,\x00\xb1\xff@\"\x00\xad\xff@\x18\x00\xad\xff@\x0e\x00\xae\xff@\x06\x00\xb4\xff@\x00\x00\xbc\xff@\xfe\xff\xc5\xff@\x00\x00\xd0\xff@\x03\x00\xda\xff@\x0b\x00\xe0\xff@\x15\x00\xe3\xff@\x15\x00\xed\xffH\x0e\x00\xf4\xffH\x05\x00\xf9\xffH\x0c\x00\xf2\xffH\x15\x00\xee\xffH\x1f\x00\xec\xffH)\x00\xec\xffH3\x00\xe8\xffH:\x00\xe1\xffH@\x00\xd9\xff@F\x00\xd1\xff@",
        ),
    ],
    ids=["1", "2", "3", "4"],
)
def test_decompress_base64_data_lzma(
    benchmark: BenchmarkFixture, value: str, expected: bytes
) -> None:
    """Test decompress_base64_data function with lzma base64 values."""
    result = benchmark(decompress_base64_data, value)
    assert result == expected
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
    result = benchmark(decompress_base64_data, value)
    assert result == expected


_REAL_NGIOT_LZ4_MAP = "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"
_REAL_NGIOT_LZ4_LEN = 21168
_REAL_NGIOT_LZ4_SHA256 = "11ef0e79e46c3d7617b2d1a4f3688159a94b7aea2fd24c2bee2474e0a3ea18af"


def test_decompress_base64_lz4_data_real_payload() -> None:
    """Test dedicated NGIOT LZ4 helper against an observed map payload."""
    result = decompress_base64_lz4_data(_REAL_NGIOT_LZ4_MAP, _REAL_NGIOT_LZ4_LEN)

    assert len(result) == _REAL_NGIOT_LZ4_LEN
    assert hashlib.sha256(result).hexdigest() == _REAL_NGIOT_LZ4_SHA256
    assert result[:16] == b"\x7f" * 16
    assert set(result).issuperset({0, 1, 2, 127, 255})


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
        decompress_base64_data(value)


@pytest.mark.parametrize(
    ("value", "expected_len", "expected_error"),
    [
        ("@@not-base64@@", 10, "Invalid symbol"),
        (base64.b64encode(b"abc").decode(), 0, "Invalid LZ4 expected length: 0"),
        (base64.b64encode(b"abc").decode(), 10, "LZ4 decompress failed"),
    ],
)
def test_decompress_base64_lz4_data_errors(
    value: str, expected_len: int, expected_error: str
) -> None:
    """Test NGIOT LZ4 helper failure cases."""
    with pytest.raises(ValueError, match=expected_error):
        decompress_base64_lz4_data(value, expected_len)



def _decompress_7z_base64_data_python(data: str) -> bytes:
    """Decompress base64 decoded 7z compressed string."""
    final_array = bytearray()

    decoded = base64.b64decode(data)

    for i, idx in enumerate(decoded):
        if i == 8:
            final_array.extend(b"\x00\x00\x00\x00")
        final_array.append(idx)

    dec = lzma.LZMADecompressor(lzma.FORMAT_AUTO, None, None)
    return dec.decompress(final_array)