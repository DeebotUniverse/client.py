from __future__ import annotations

import pytest

from deebot_client.events import Event, StateEvent
from deebot_client.message import HandlingState
from deebot_client.messages.xml import ChargeState
from deebot_client.models import State
from tests.messages import assert_message, assert_message_failure


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
async def test_charge_state(state: str, expected_event: Event) -> None:
    xml_message = f'<ctl ts="1745329944849" td="ChargeState"><charge type="{state}" h="" r="" s="" g="0" /></ctl>'
    assert_message(ChargeState, xml_message, expected_event)


@pytest.mark.parametrize(
    "xml_message",
    [
        '<ctl ts="1745329944849" td="ChargeState" />',
    ],
    ids=["missing_payload"],
)
async def test_charge_state_error(xml_message: str) -> None:
    assert_message_failure(ChargeState, xml_message, HandlingState.ANALYSE_LOGGED)
