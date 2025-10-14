from __future__ import annotations

import pytest

from deebot_client.events import Event, StateEvent
from deebot_client.message import HandlingState
from deebot_client.messages.xml import ChargeState
from deebot_client.models import State
from tests.messages import assert_message_failure
from tests.messages.xml import assert_message


@pytest.mark.parametrize(
    ("state", "expected_event"),
    [
        ("SlotCharging", StateEvent(State.DOCKED)),
        ("Going", StateEvent(State.RETURNING)),
        ("unknown state returned", StateEvent(State.ERROR)),
    ],
    ids=["slot_charging", "going", "unknown"],
)
async def test_charge_state(state: str, expected_event: Event) -> None:
    xml_message = f'<ctl ts="1745329944849" td="ChargeState"><charge type="{state}" h="" r="" s="" g="0" /></ctl>'
    await assert_message(ChargeState, xml_message, expected_event)


@pytest.mark.parametrize(
    "xml_message",
    [
        '<ctl ts="1745329944849" td="ChargeState" />',
        '<ctl ts="1745329944849" td="ChargeState"><charge type="Idle" h="" r="" s="" g="0" /></ctl>',
    ],
    ids=["missing_payload", "idle"],
)
async def test_charge_state_error(xml_message: str) -> None:
    assert_message_failure(ChargeState, xml_message, HandlingState.ANALYSE_LOGGED)
