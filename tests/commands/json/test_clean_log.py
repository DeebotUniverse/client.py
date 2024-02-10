from __future__ import annotations

import logging
from typing import Any

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.json import GetCleanLogs
from deebot_client.events import CleanJobStatus, CleanLogEntry, CleanLogEvent
from deebot_client.message import HandlingState

from . import assert_command


async def test_GetCleanLogs(caplog: pytest.LogCaptureFixture) -> None:
    json = {
        "ret": "ok",
        "logs": [
            {
                "ts": 1656265100,
                "last": 139,
                "area": 2,
                "id": "acb2e78e-8f25-454a-a0ac-***@***@iCmB",
                "imageUrl": "https://portal-eu.ecouser.net/api/lg/image/acb2e78e-8f25-454a-a0ac-***@***@iCmB",
                "type": "spotArea",
                "aiavoid": 0,
                "aitypes": [],
                "stopReason": 1,
                "aiopen": 1,
                "powerMopType": 1,
            },
            {
                "ts": 1655564615,
                "last": 366,
                "area": 0,
                "id": "acb2e78e-8f25-454a-a0ac-***@***@iCmB",
                "imageUrl": "https://portal-eu.ecouser.net/api/lg/image/acb2e78e-8f25-454a-a0ac-***@***@iCmB",
                "type": "auto",
                "aiavoid": 0,
                "aitypes": [],
                "aiopen": 1,
                "powerMopType": 1,
            },
            {
                "ts": 1655564399,
                "last": 61,
                "area": 0,
                "id": "acb2e78e-8f25-454a-a0ac-***@***@iCmB",
                "imageUrl": "https://portal-eu.ecouser.net/api/lg/image/acb2e78e-8f25-454a-a0ac-***@***@iCmB",
                "type": "spotArea",
                "aiavoid": 0,
                "aitypes": [],
                "stopReason": 2,
                "aiopen": 1,
                "powerMopType": 1,
            },
            {
                "ts": 1655564222,
                "last": 73,
                "area": 0,
                "id": "acb2e78e-8f25-454a-a0ac-***@***@iCmB",
                "imageUrl": "https://portal-eu.ecouser.net/api/lg/image/acb2e78e-8f25-454a-a0ac-***@***@iCmB",
                "type": "spotArea",
                "aiavoid": 0,
                "aitypes": [],
                "stopReason": 3,
                "aiopen": 1,
                "powerMopType": 1,
            },
            {"ts": 1655564616, "invalid": "event"},
        ],
    }

    expected = CleanLogEvent(
        [
            CleanLogEntry(
                timestamp=1656265100,
                image_url="https://portal-eu.ecouser.net/api/lg/image/acb2e78e-8f25-454a-a0ac-***@***@iCmB",
                type="spotArea",
                area=2,
                stop_reason=CleanJobStatus.FINISHED,
                duration=139,
            ),
            CleanLogEntry(
                timestamp=1655564615,
                image_url="https://portal-eu.ecouser.net/api/lg/image/acb2e78e-8f25-454a-a0ac-***@***@iCmB",
                type="auto",
                area=0,
                stop_reason=CleanJobStatus.NO_STATUS,
                duration=366,
            ),
            CleanLogEntry(
                timestamp=1655564399,
                image_url="https://portal-eu.ecouser.net/api/lg/image/acb2e78e-8f25-454a-a0ac-***@***@iCmB",
                type="spotArea",
                area=0,
                stop_reason=CleanJobStatus.MANUAL_STOPPED,
                duration=61,
            ),
            CleanLogEntry(
                timestamp=1655564222,
                image_url="https://portal-eu.ecouser.net/api/lg/image/acb2e78e-8f25-454a-a0ac-***@***@iCmB",
                type="spotArea",
                area=0,
                stop_reason=CleanJobStatus.FINISHED_WITH_WARNINGS,
                duration=73,
            ),
        ]
    )

    await assert_command(GetCleanLogs(), json, expected)

    assert (
        "deebot_client.commands.json.clean_logs",
        logging.WARNING,
        "Skipping log entry: {'ts': 1655564616, 'invalid': 'event'}",
    ) in caplog.record_tuples


@pytest.mark.parametrize(
    "json",
    [{"ret": "ok"}, {"ret": "fail"}],
)
async def test_GetCleanLogs_analyse_logged(
    json: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    await assert_command(
        GetCleanLogs(),
        json,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )

    assert (
        "deebot_client.command",
        logging.DEBUG,
        f"ANALYSE: Could not handle command: GetCleanLogs with {json}",
    ) in caplog.record_tuples


async def test_GetCleanLogs_handle_error(caplog: pytest.LogCaptureFixture) -> None:
    await assert_command(
        GetCleanLogs(),
        {},
        None,
        command_result=CommandResult(HandlingState.ERROR),
    )

    assert (
        "deebot_client.command",
        logging.WARNING,
        f"Could not parse response for {GetCleanLogs.name}: {{}}",
    ) in caplog.record_tuples
