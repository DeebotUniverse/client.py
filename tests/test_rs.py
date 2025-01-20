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
def test_decompress_7z_base64_data(input: str, expected: bytes) -> None:
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
