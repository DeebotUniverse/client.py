"""Test events."""

from __future__ import annotations

import pytest

from deebot_client.events import LifeSpan, SweepType, WaterAmount, WaterInfoEvent


def test_life_span() -> None:
    """Test life span events."""
    assert LifeSpan.BRUSH != LifeSpan.FILTER  # type: ignore[comparison-overlap]
    assert LifeSpan.FILTER not in {LifeSpan.BLADE, LifeSpan.BRUSH, LifeSpan.SIDE_BRUSH}


def test_water_info() -> None:
    """Test water info events."""
    # Those are OK
    WaterInfoEvent(amount=WaterAmount.HIGH)
    WaterInfoEvent(sweep_type=SweepType.STANDARD)
    WaterInfoEvent(mop_attached=False)

    # This is not
    with pytest.raises(
        ValueError, match="A WaterInfoEvent must contain at least one value"
    ):
        WaterInfoEvent()
