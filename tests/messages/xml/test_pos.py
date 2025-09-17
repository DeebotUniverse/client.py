from __future__ import annotations

import pytest

from deebot_client.events import Position, PositionsEvent
from deebot_client.message import HandlingState
from deebot_client.messages.xml import Pos
from deebot_client.rs.map import PositionType
from tests.messages import assert_message, assert_message_failure


@pytest.mark.parametrize("position", [(-9, 15, 89)])
def test_Pos(position: tuple[int, int, int]) -> None:
    x, y, a = position
    xml_message = f'<ctl td="Pos" t="p" p="{x},{y}" a="{a}" valid="1" />'
    assert_message(
        Pos,
        xml_message,
        PositionsEvent([Position(type=PositionType.DEEBOT, x=x, y=y, a=a)]),
    )


@pytest.mark.parametrize(
    "xml_message",
    sorted(
        {
            '<ctl td="Pos" t="p" a="89" valid="1" />',
            '<ctl td="Pos" t="??" p="0,0" a="89" valid="1" />',
            '<ctl td="Pos" t="p" p="0,0" a="89" valid="0" />',
        }
    ),
)
def test_Pos_error(xml_message: str) -> None:
    assert_message_failure(Pos, xml_message, HandlingState.ANALYSE_LOGGED)
