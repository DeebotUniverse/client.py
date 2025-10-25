from __future__ import annotations

import pytest

from deebot_client.events import BatteryEvent
from deebot_client.message import HandlingState
from deebot_client.messages.xml import BatteryInfo
from tests.messages import assert_message_failure
from tests.messages.xml import assert_message


@pytest.mark.parametrize("percentage", [0, 49, 100])
@pytest.mark.benchmark
def test_BatteryInfo(percentage: int) -> None:
    xml_message = f'<ctl ret="ok"><battery power="{percentage}" /></ctl>'

    assert_message(BatteryInfo, xml_message, BatteryEvent(percentage))


@pytest.mark.parametrize(
    "xml_message",
    [
        '<ctl ret="ok"><battery /></ctl>',
        '<ctl ret="ok"><battery power="-1" /></ctl>',
        '<ctl ret="ok"><battery power="fake" /></ctl>',
        '<ctl ret="ok"><wrong power="100" /></ctl>',
    ],
)
@pytest.mark.benchmark
def test_BatteryInfo_error(xml_message: str) -> None:
    assert_message_failure(BatteryInfo, xml_message, HandlingState.ANALYSE_LOGGED)
