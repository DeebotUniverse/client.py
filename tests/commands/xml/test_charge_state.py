from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.xml import GetChargeState
from deebot_client.events import StateEvent
from deebot_client.message import HandlingState
from deebot_client.models import State
from tests.commands import assert_command

from . import get_request_xml

if TYPE_CHECKING:
    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    ("state", "expected_event"),
    [
        ("SlotCharging", StateEvent(State.DOCKED)),
        ("Idle", StateEvent(State.IDLE)),
        ("Going", StateEvent(State.RETURNING)),
        ("unknown state returned", StateEvent(State.ERROR)),
    ],
    ids=["slot_charging", "idle", "going", "unknown"],
)
async def test_get_charge_state(state: str, expected_event: Event) -> None:
    json = get_request_xml(f"<ctl ret='ok'><charge type='{state}' g='0'/></ctl>")
    await assert_command(GetChargeState(), json, expected_event)


@pytest.mark.parametrize(
    "xml",
    ["<ctl ret='error'/>", "<ctl ret='ok'></ctl>"],
    ids=["error", "no_state"],
)
async def test_get_charge_state_error(xml: str) -> None:
    json = get_request_xml(xml)
    await assert_command(
        GetChargeState(),
        json,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )
