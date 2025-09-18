from __future__ import annotations

import pytest

from deebot_client.events import (
    CleanJobStatus,
    Event,
    FanSpeedEvent,
    FanSpeedLevel,
    Position,
    PositionsEvent,
    ReportStatsEvent,
    StateEvent,
    StatsEvent,
)
from deebot_client.message import HandlingState
from deebot_client.messages.xml import CleanReportServer
from deebot_client.messages.xml.clean import CleanedPos, CleanReport, CleanSt
from deebot_client.models import State
from deebot_client.rs.map import PositionType
from tests.messages import assert_message, assert_message_failure


def test_CleanSt() -> None:
    xml_message = "<ctl td='CleanSt' a='21' s='1743945874' l='1595' t='' type='auto'/>"
    assert_message(CleanSt, xml_message, None)


@pytest.mark.parametrize(
    ("params", "expected_events"),
    [
        (
            "speed='standard' st='s'",
            [FanSpeedEvent(FanSpeedLevel.NORMAL), StateEvent(State.CLEANING)],
        ),
        (
            "speed='strong' st='s'",
            [FanSpeedEvent(FanSpeedLevel.MAX), StateEvent(State.CLEANING)],
        ),
        (
            "speed='standard' st='p'",
            [FanSpeedEvent(FanSpeedLevel.NORMAL), StateEvent(State.PAUSED)],
        ),
        (
            "st='r'",
            [StateEvent(State.CLEANING)],
        ),
        (
            "st='h'",
            [StateEvent(State.IDLE)],
        ),
        (
            "speed='strong'",
            [FanSpeedEvent(FanSpeedLevel.MAX)],
        ),
    ],
    ids=[
        "standard_cleaning",
        "strong_cleaning",
        "paused",
        "resume/cleaning",
        "stop/idle",
        "fanspeed_only",
    ],
)
def test_CleanReport(
    params: str,
    expected_events: list[Event],
) -> None:
    xml_message = f"<ctl ts='1744467249311' td='CleanReport'><clean type='auto' {params} rsn='a' a='' l='' sts=''/></ctl>"
    assert_message(
        CleanReport,
        xml_message,
        expected_events,
    )


@pytest.mark.parametrize(
    ("params", "expected_events"),
    [
        (
            "act='s' type='auto' cs='1134230540'",
            [
                ReportStatsEvent(
                    area=None,
                    time=None,
                    type="auto",
                    cleaning_id="1134230540",
                    status=CleanJobStatus.CLEANING,
                    content=[],
                )
            ],
        ),
        (
            "act='h' type='auto' area='1' last='76' cs='1134230540'",
            [
                StatsEvent(area=1, time=76, type="auto"),
                ReportStatsEvent(
                    area=1,
                    time=76,
                    type="auto",
                    cleaning_id="1134230540",
                    status=CleanJobStatus.FINISHED,
                    content=[],
                ),
            ],
        ),
        (
            "act='p' type='auto' area='1' last='76' cs='1134230540'",
            [
                ReportStatsEvent(
                    area=1,
                    time=76,
                    type="auto",
                    cleaning_id="1134230540",
                    status=CleanJobStatus.MANUALLY_STOPPED,
                    content=[],
                ),
            ],
        ),
        (
            "act='r' type='auto' area='1' last='76' cs='1134230540'",
            [
                ReportStatsEvent(
                    area=1,
                    time=76,
                    type="auto",
                    cleaning_id="1134230540",
                    status=CleanJobStatus.CLEANING,
                    content=[],
                ),
            ],
        ),
    ],
)
def test_CleanReportServer(params: str, expected_events: list[Event]) -> None:
    xml_message = f"<ctl ts='1744467393682' td='CleanReportServer' {params} />"
    assert_message(
        CleanReportServer,
        xml_message,
        expected_events,
    )


@pytest.mark.parametrize(
    "xml_message",
    [
        "<ctl ts='1744467393682' td='CleanReportServer' type='auto' sts='1744467262' cs='1134230540' area='1' last='76' mapCount='6'/>",
        "<ctl ts='1744467393682' td='CleanReportServer' act='r' />",
    ],
    ids=["missing_act", "missing_clean_session"],
)
def test_CleanReportServer_error(xml_message: str) -> None:
    assert_message_failure(
        CleanReportServer,
        xml_message,
        HandlingState.ANALYSE_LOGGED,
    )


@pytest.mark.parametrize(
    "xml",
    [
        "<ctl ts='1744467249311' td='CleanReport' />",
        "<ctl ts='1744467249311' td='CleanReport'><clean /></ctl>",
    ],
    ids=["error", "no_state"],
)
def test_CleanReport_error(xml: str) -> None:
    assert_message_failure(
        CleanReport,
        xml,
        HandlingState.ANALYSE_LOGGED,
    )


@pytest.mark.parametrize("position", [(-9, 15, 89)])
def test_CleanedPos(position: tuple[int, int, int]) -> None:
    x, y, a = position
    xml_message = f"<ctl ts='1744467393682' td='CleanedPos' t='p' p='{x},{y}' a='{a}' csid='1134230540'/>"

    assert_message(
        CleanedPos,
        xml_message,
        PositionsEvent([Position(type=PositionType.DEEBOT, x=x, y=y, a=a)]),
    )


@pytest.mark.parametrize(
    "xml_message",
    sorted(
        {
            '<ctl ts="1744467393682" td="CleanedPos" t="p" a="89" csid="1134230540" />',
            '<ctl ts="1744467393682" td="CleanedPos" t="??" p="0,0" a="89" csid="1134230540@" />',
            "<ctl />",
        }
    ),
)
def test_CleanedPos_error(xml_message: str) -> None:
    assert_message_failure(CleanedPos, xml_message, HandlingState.ANALYSE_LOGGED)
