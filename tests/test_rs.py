"""Test rust functions."""

from __future__ import annotations

import pytest

from deebot_client.rs import decompress_7z_base64_data


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
    ],
)
def test_decompress_7z_base64_data(input: str, expected: str) -> None:
    """Test decompress_7z_base64_data function."""
    assert decompress_7z_base64_data(input) == expected
