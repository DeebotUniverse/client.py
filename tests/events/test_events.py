"""Test events."""

from __future__ import annotations

import pytest

from deebot_client.events import LifeSpan


def test_life_span() -> None:
    """Test life span events."""
    assert LifeSpan.BRUSH != LifeSpan.FILTER  # type: ignore[comparison-overlap]
    assert LifeSpan.FILTER not in {LifeSpan.BLADE, LifeSpan.BRUSH, LifeSpan.SIDE_BRUSH}


@pytest.mark.parametrize("value", list(LifeSpan))
def test_life_span_xml_conversion(value: LifeSpan) -> None:
    assert LifeSpan.from_xml(value.xml_value) == value


@pytest.mark.parametrize("value", list(LifeSpan))
def test_life_span_conversion(value: LifeSpan) -> None:
    assert LifeSpan(value.value) == value
