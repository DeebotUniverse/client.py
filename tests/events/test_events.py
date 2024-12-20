"""Test events."""

from __future__ import annotations

from deebot_client.events import LifeSpan


def test_life_span() -> None:
    """Test life span events."""
    assert LifeSpan.BRUSH != LifeSpan.FILTER
    assert LifeSpan.FILTER not in {LifeSpan.BLADE, LifeSpan.BRUSH, LifeSpan.SIDE_BRUSH}
