"""Tests for native map id validation."""

from __future__ import annotations

import pytest

from deebot_client.map_ids import valid_mid


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("2", "2"),
        ("  3  ", "3"),
        (5, "5"),
        (1, "1"),
    ],
)
def test_valid_mid_accepts_str_and_int(raw: object, want: str) -> None:
    """Given str/int ids, when validated, then trimmed string."""
    assert valid_mid(raw) == want


@pytest.mark.parametrize(
    "raw",
    [None, "", "   ", "0", " 0 ", 0, True, False, 1.5, 2.0, ["2"], ("2",), {"id": "2"}],
)
def test_valid_mid_rejects_non_id_values(raw: object) -> None:
    """Given bool/float/collection/empty ids, when validated, then None."""
    assert valid_mid(raw) is None
