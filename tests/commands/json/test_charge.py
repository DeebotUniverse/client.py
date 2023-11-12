import logging
from typing import Any

import pytest

from deebot_client.commands.json import Charge
from deebot_client.events import StateEvent
from deebot_client.models import State
from tests.helpers import get_request_json, get_success_body

from . import assert_command


def _prepare_json(code: int, msg: str = "ok") -> dict[str, Any]:
    json = get_request_json(get_success_body())
    json["resp"]["body"].update(
        {
            "code": code,
            "msg": msg,
        }
    )
    return json


@pytest.mark.parametrize(
    ("json", "expected"),
    [
        (get_request_json(get_success_body()), StateEvent(State.RETURNING)),
        (_prepare_json(30007), StateEvent(State.DOCKED)),
    ],
)
async def test_Charge(json: dict[str, Any], expected: StateEvent) -> None:
    await assert_command(Charge(), json, expected)


async def test_Charge_failed(caplog: pytest.LogCaptureFixture) -> None:
    json = _prepare_json(500, "fail")
    await assert_command(Charge(), json, None)

    assert (
        "deebot_client.commands.json.common",
        logging.WARNING,
        f"Command \"charge\" was not successfully. body={json['resp']['body']}",
    ) in caplog.record_tuples
