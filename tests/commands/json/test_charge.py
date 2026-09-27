from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from deebot_client.commands.json import Charge
from deebot_client.events import FirmwareEvent, StateEvent
from deebot_client.message import HandlingResult, HandlingState
from deebot_client.models import State
from tests.helpers import get_request_json, get_success_body

from . import assert_command

if TYPE_CHECKING:
    from deebot_client.event_bus import EventBus


def _prepare_json(code: int, msg: str = "ok") -> tuple[dict[str, Any], FirmwareEvent]:
    json, firmware_event = get_request_json(get_success_body())
    json["resp"]["body"].update(
        {
            "code": code,
            "msg": msg,
        }
    )
    return json, firmware_event


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (get_request_json(get_success_body()), StateEvent(State.RETURNING)),
        (_prepare_json(30007), StateEvent(State.DOCKED)),
    ],
)
async def test_Charge(
    data: tuple[dict[str, Any], FirmwareEvent], expected: StateEvent
) -> None:
    json, firmware_event = data
    await assert_command(Charge(), json, (firmware_event, expected))


async def test_Charge_failed(caplog: pytest.LogCaptureFixture) -> None:
    json, firmware_event = _prepare_json(500, "fail")
    await assert_command(
        Charge(),
        json,
        firmware_event,
        handling_result=HandlingResult(HandlingState.FAILED),
    )

    assert (
        "deebot_client.commands.json.common",
        logging.WARNING,
        f'Command "charge" was not successfully. body={json["resp"]["body"]}',
    ) in caplog.record_tuples


@pytest.mark.parametrize("device_class", ["300lc5", "yna5xi"])
@pytest.mark.parametrize("code", [0, 30007, 20003])
async def test_charge_ack_refreshes_mower_activity(
    event_bus: EventBus, device_class: str, code: int
) -> None:
    with patch.object(event_bus, "request_refresh") as refresh:
        Charge.handle(event_bus, {"body": {"code": code}})
        if device_class == "300lc5" and code in (0, 30007):
            refresh.assert_called_once_with(StateEvent, queue_if_busy=True)
        else:
            refresh.assert_not_called()
