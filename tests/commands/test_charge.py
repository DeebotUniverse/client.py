from typing import Any

import pytest
from testfixtures import LogCapture

from deebot_client.commands import Charge
from deebot_client.events import StatusEvent
from deebot_client.models import VacuumState
from tests.commands import assert_command_requested
from tests.helpers import get_request_json


def _prepare_json(code: int, msg: str = "ok") -> dict[str, Any]:
    json = get_request_json(None)
    json["resp"]["body"].update(
        {
            "code": code,
            "msg": msg,
        }
    )
    return json


@pytest.mark.parametrize(
    "json, expected",
    [
        (get_request_json(None), StatusEvent(True, VacuumState.RETURNING)),
        (_prepare_json(30007), StatusEvent(True, VacuumState.DOCKED)),
    ],
)
async def test_Charge(json: dict[str, Any], expected: StatusEvent) -> None:
    await assert_command_requested(Charge(), json, expected)


async def test_Charge_failed() -> None:
    with LogCapture() as log:
        json = _prepare_json(500, "fail")
        await assert_command_requested(Charge(), json, None)

        log.check_present(
            (
                "deebot_client.commands.common",
                "WARNING",
                f"Command \"charge\" was not successfully. body={json['resp']['body']}",
            )
        )
