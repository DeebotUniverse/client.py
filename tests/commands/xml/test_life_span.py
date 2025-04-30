from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.xml import GetLifeSpan, ResetLifeSpan
from deebot_client.events import LifeSpan, LifeSpanEvent
from deebot_client.message import HandlingState
from tests.commands import assert_command

from . import (
    assert_execute_command,
    get_failure_body,
    get_request_xml,
    get_success_body,
)

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


@pytest.mark.parametrize(
    ("component_type", "lifespan_type", "left", "total", "expected_event"),
    [
        ("Brush", LifeSpan.BRUSH, 50, 100, LifeSpanEvent(LifeSpan.BRUSH, 50, 50)),
        (
            "Brush",
            LifeSpan.BRUSH.xml_value,
            50,
            100,
            LifeSpanEvent(LifeSpan.BRUSH, 50, 50),
        ),
        (
            "DustCaseHeap",
            LifeSpan.DUST_CASE_HEAP,
            50,
            200,
            LifeSpanEvent(LifeSpan.DUST_CASE_HEAP, 25, 50),
        ),
        (
            "SideBrush",
            LifeSpan.SIDE_BRUSH,
            25,
            200,
            LifeSpanEvent(LifeSpan.SIDE_BRUSH, 12.5, 25),
        ),
    ],
)
async def test_get_life_span(
    component_type: str,
    lifespan_type: LifeSpan | str,
    left: int,
    total: int,
    expected_event: LifeSpanEvent,
) -> None:
    xml = get_request_xml(
        f"<ctl ret='ok' type='{component_type}' left='{left}' total='{total}'/>"
    )
    await assert_command(GetLifeSpan(lifespan_type), xml, expected_event)


@pytest.mark.parametrize(
    "xml",
    ["<ctl ret='error'/>", "<ctl ret='ok' type='SideBrush' left='123' />"],
    ids=["error", "no_state"],
)
async def test_get_life_span_error(xml: str) -> None:
    json = get_request_xml(xml)
    await assert_command(
        GetLifeSpan(LifeSpan.BRUSH),
        json,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )


@pytest.mark.parametrize(
    ("command", "args"),
    [
        (ResetLifeSpan(LifeSpan.FILTER), {"type": LifeSpan.FILTER.xml_value}),
        (ResetLifeSpan(LifeSpan.FILTER.xml_value), {"type": LifeSpan.FILTER.xml_value}),
        (
            ResetLifeSpan.create_from_mqtt(b'<ctl type="Brush" />'),
            {"type": LifeSpan.BRUSH.xml_value},
        ),
    ],
)
async def test_ResetLifeSpan(command: ResetLifeSpan, args: dict[str, str]) -> None:
    await assert_execute_command(command, args)


def test_ResetLifeSpan_invokes_refresh(event_bus: EventBus) -> None:
    command = ResetLifeSpan(LifeSpan.FILTER)
    success_response = get_success_body()

    with patch.object(
        event_bus, "request_refresh", return_value=None
    ) as mock_request_refresh:
        command.handle_mqtt_p2p(event_bus, success_response)

    mock_request_refresh.assert_called_with(LifeSpanEvent)


def test_ResetLifeSpan_not_invokes_refresh(event_bus: EventBus) -> None:
    command = ResetLifeSpan(LifeSpan.FILTER)
    failure_response = get_failure_body()

    with patch.object(
        event_bus, "request_refresh", return_value=None
    ) as mock_request_refresh:
        command.handle_mqtt_p2p(event_bus, failure_response)

    mock_request_refresh.assert_not_called()
