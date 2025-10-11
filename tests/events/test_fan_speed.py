from __future__ import annotations

import pytest

from deebot_client.events import FanSpeedLevel


@pytest.mark.parametrize("value", [level for level in FanSpeedLevel if level.xml_value])
def test_clean_action_xml_conversion(value: FanSpeedLevel) -> None:
    assert FanSpeedLevel.from_xml(value.xml_value) == value


@pytest.mark.parametrize("value", list(FanSpeedLevel))
def test_clean_action_conversion(value: FanSpeedLevel) -> None:
    assert FanSpeedLevel(value.value) == value
