from __future__ import annotations

from typing import Any

import pytest

from deebot_client.commands.json import GetQuickCommand
from deebot_client.events import ScenariosEvent
from deebot_client.models import Scenario
from tests.helpers import get_request_json, get_success_body

from . import assert_command


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (
            [
                {
                    "array": [
                        {
                            "content": "1,5,,1,1000,30,0,2;1,3,,2,2,50,0,1",
                            "icon": "map-customize-mop",
                            "mid": "199390082",
                            "name": "Mopping",
                            "qcid": "5802",
                            "state": 0,
                            "type": 1,
                        },
                        {
                            "content": "1,3,,2,2,45,0,2;1,8,,1,2,40,3,1",
                            "icon": "map-customize-daily",
                            "mid": "199390082",
                            "name": "Mopping intensive",
                            "qcid": "5249",
                            "state": 0,
                            "type": 1,
                        },
                    ],
                    "mid": "199390082",
                    "sort": "",
                }
            ],
            ScenariosEvent(
                [
                    Scenario("5802", "Mopping", "199390082"),
                    Scenario("5249", "Mopping intensive", "199390082"),
                ]
            ),
        ),
        (
            [
                {
                    "array": [{"name": "Daily vacuum", "qcid": 5670}],
                    "mid": "1475209183",
                },
                {"array": [], "mid": "1475209184"},
            ],
            ScenariosEvent([Scenario("5670", "Daily vacuum", "1475209183")]),
        ),
    ],
    ids=["one map", "map id from group"],
)
async def test_GetQuickCommand(
    data: list[dict[str, Any]], expected: ScenariosEvent
) -> None:
    command = GetQuickCommand()
    assert command._args == {"type": "1,2,4"}

    json, firmware_event = get_request_json(get_success_body(data))
    await assert_command(command, json, [firmware_event, expected])
