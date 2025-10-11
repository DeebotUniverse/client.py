from __future__ import annotations

import pytest

from deebot_client.models import CleanAction, CleanMode


@pytest.mark.parametrize("value", list(CleanAction))
def test_clean_action_xml_conversion(value: CleanAction) -> None:
    assert CleanAction.from_xml(value.xml_value) == value


@pytest.mark.parametrize("value", list(CleanAction))
def test_clean_action_conversion(value: CleanAction) -> None:
    assert CleanAction(value.value) == value


@pytest.mark.parametrize("value", list(CleanMode))
def test_clean_mode_xml_conversion(value: CleanMode) -> None:
    assert CleanMode.from_xml(value.xml_value) == value


@pytest.mark.parametrize("value", list(CleanMode))
def test_clean_mode_conversion(value: CleanMode) -> None:
    assert CleanMode(value.value) == value
