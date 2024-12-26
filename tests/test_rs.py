"""Test rust functions."""

from __future__ import annotations

import base64
import lzma
from typing import TYPE_CHECKING, Any

import pytest

from deebot_client.rs import decompress_7z_base64_data

if TYPE_CHECKING:
    from contextlib import AbstractContextManager


@pytest.mark.parametrize(
    ("input", "expected"),
    [
        (
            "XQAABACZAAAAABaOQmW9Bsibxz42rKUpGlV7Rr4D1S/9x9mDa60v4J1BKrEsnk34EAt6X5gKkxwYzfOu3T8GAPpmIy5o4A==",
            "-9125,3225;-9025,3225;-8975,3175;-8975,2475;-8925,2425;-8925,2375;-8325,2375;-8275,2425;-8225,2375;-8225,2425;-8174,2475;-8024,2475;-8024,4375;-9125,4375",
        ),
        (
            "XQAABABBAAAAAC2WwEIwUhHX3vfFDfs1H1PUqtdWgakwVnMBz3Bb3yaoE5OYkdYA",
            '[["4","-6217","3919","-6217","231","-2642","231","-2642","3919"]]',
        ),
        (
            "XQAABADHAAAAAC2WwEHwYhHX3vWwDK80QCnaQU0mwUd9Vk34ub6OxzOk6kdFfbFvpVp4iIlKisAvp0MznQNYEZ8koxFHnO+iM44GUKgujGQKgzl0bScbQgaon1jI3eyCRikWlkmrbwA=",
            '[["0","-5195","-1059","-5195","-37","-5806","-37","-5806","-1059"],["1","-7959","220","-7959","1083","-9254","1083","-9254","220"],["2","-9437","347","-5387","410"],["3","-5667","317","-4888","-56"]]',
        ),
    ],
)
def test_decompress_7z_base64_data(input: str, expected: str) -> None:
    """Test decompress_7z_base64_data function."""
    assert _decompress_7z_base64_data_python(input) == expected
    assert decompress_7z_base64_data(input) == expected


@pytest.mark.parametrize(
    ("input", "error"),
    [
        (
            "XQAABADHAAAAAC2WwEHwYhHX3vWwDK80QCnaQU0mwUd9Vk34ub6OxzOk6kdFfbFvpVp4iIlKisAvp0MznQNYEZ8koxFHnO,+iM44GUKgujGQKgzl0bScbQgaon1jI3eyCRikWlkmrbwA=",
            pytest.raises(ValueError, match="Invalid symbol 44, offset 94."),
        ),
        (
            "XQAABABBAAAAAC2WwEIwUhHX3vfFDfs1H1PUqtdWgakwVnMBz3Bb3yaoE5OYkd",
            pytest.raises(ValueError, match="Invalid padding"),
        ),
    ],
)
def test_decompress_7z_base64_data_errors(
    input: str, error: AbstractContextManager[Any]
) -> None:
    """Test decompress_7z_base64_data function."""
    with error:
        assert decompress_7z_base64_data(input)


def _decompress_7z_base64_data_python(data: str) -> str:
    """Decompress base64 decoded 7z compressed string."""
    final_array = bytearray()

    # Decode Base64
    decoded = base64.b64decode(data)

    for i, idx in enumerate(decoded):
        if i == 8:
            final_array.extend(b"\x00\x00\x00\x00")
        final_array.append(idx)

    dec = lzma.LZMADecompressor(lzma.FORMAT_AUTO, None, None)
    return dec.decompress(final_array).decode()
