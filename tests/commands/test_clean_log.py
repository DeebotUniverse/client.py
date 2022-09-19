from typing import Any
from unittest.mock import Mock

import pytest
from testfixtures import LogCapture

from deebot_client.commands import GetCleanLogs
from deebot_client.commands.common import CommandResult
from deebot_client.events import CleanJobStatus, CleanLogEntry, CleanLogEvent
from deebot_client.events.event_bus import EventBus
from deebot_client.message import HandlingState
from tests.commands import assert_command_requestedOLD
from tests.commands import assert_command_requestedOLD as assert_command_requested


def test_GetCleanLogs() -> None:
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

    with LogCapture() as log:
        assert_command_requested(GetCleanLogs(), json, expected)

        log.check_present(
            (
                "deebot_client.commands.clean_logs",
                "WARNING",
                "Skipping log entry: {'ts': 1655564616, 'invalid': 'event'}",
            )
        )


@pytest.mark.parametrize(
    "json",
    [{"ret": "ok"}, {"ret": "fail"}],
)
def test_GetCleanLogs_analyse_logged(json: dict[str, Any]) -> None:
    with LogCapture() as log:
        assert_command_requestedOLD(
            GetCleanLogs(),
            json,
            None,
            CommandResult(HandlingState.ANALYSE_LOGGED),
        )
        log.check_present(
            (
                "deebot_client.commands.common",
                "DEBUG",
                f"Could not handle command: GetCleanLogs with {json}",
            )
        )


def test_GetCleanLogs_handle_fails() -> None:
    with LogCapture() as log:
        result = GetCleanLogs.handle(Mock(spec_set=EventBus), {})

        assert result.state == HandlingState.ERROR
        log.check_present(
            (
                "deebot_client.message",
                "WARNING",
                f"Could not parse {GetCleanLogs.name}: {{}}",
            )
        )
