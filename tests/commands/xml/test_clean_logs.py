from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deebot_client.command import CommandResult
from deebot_client.commands.xml import GetCleanLogs
from deebot_client.events import CleanJobStatus, CleanLogEntry, CleanLogEvent
from deebot_client.message import HandlingState
from tests.commands import assert_command

from . import get_request_xml

if TYPE_CHECKING:
    from deebot_client.events.base import Event


@pytest.mark.parametrize(
    ("payload", "expected_event"),
    [
        (
            "<CleanSt a='0' s='1710433763' l='14' t='' f='s'/><CleanSt a='1' s='1710433269' l='22' t='' f='s'/>",
            CleanLogEvent(
                [
                    CleanLogEntry(1710433763, "", "", 0, CleanJobStatus.FINISHED, 14),
                    CleanLogEntry(1710433269, "", "", 1, CleanJobStatus.FINISHED, 22),
                ]
            ),
        ),
        (
            "<CleanSt a='20' s='1710244976' l='1392' t='a' f='a'/>"
            "<CleanSt a='wrong' s='1710083567' l='894' t='a' f='a'/>"
            "<CleanSt a='21' s='1710244999' l='2392' t='a' f='????'/>",
            CleanLogEvent(
                [
                    CleanLogEntry(
                        1710244976, "", "a", 20, CleanJobStatus.MANUALLY_STOPPED, 1392
                    ),
                    CleanLogEntry(
                        1710244999, "", "a", 21, CleanJobStatus.FINISHED, 2392
                    ),
                ]
            ),
        ),
        ("", CleanLogEvent([])),
    ],
    ids=["finished_two_areas", "skipping_invalid_data", "no_data"],
)
async def test_get_clean_logs(payload: str, expected_event: Event | None) -> None:
    json = get_request_xml(f"<ctl ret='ok'>{payload}</ctl>")
    await assert_command(GetCleanLogs(count=3), json, expected_event)


@pytest.mark.parametrize(
    "xml",
    ["<ctl ret='error'/>"],
    ids=["error"],
)
async def test_get_clean_logs_error(xml: str) -> None:
    json = get_request_xml(xml)
    await assert_command(
        GetCleanLogs(),
        json,
        None,
        command_result=CommandResult(HandlingState.ANALYSE_LOGGED),
    )
