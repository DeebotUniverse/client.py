from typing import Any

import pytest

from deebot_client.commands import GetChargeState
from deebot_client.events import StateEvent
from deebot_client.models import VacuumState
from tests.commands import assert_command
from tests.helpers import get_request_json, get_request_xml


@pytest.mark.parametrize(
    "json, expected",
    [
        (get_request_json({"isCharging": 0, "mode": "slot"}), None),
    ],
)
async def test_GetChargeState(
    json: dict[str, Any], expected: StateEvent | None
) -> None:
    await assert_command(GetChargeState(), json, expected)


@pytest.mark.parametrize(
    "response, expected",
    [
        (
            get_request_xml("<ctl ret='ok'><charge type='SlotCharging' g='1'/></ctl>"),
            StateEvent(VacuumState.DOCKED),
        ),
        (
            get_request_xml("<ctl ret='ok'><charge type='Idle' g='0'/></ctl>"),
            StateEvent(VacuumState.DOCKED),
        ),
    ],
)
async def test_GetChargeStateXml(
    response: dict[str, Any], expected: StateEvent
) -> None:
    await assert_command(GetChargeState(), response, expected)
