from __future__ import annotations

import pytest

from deebot_client.events import MapTraceEvent, MinorMapEvent
from deebot_client.message import HandlingState
from deebot_client.messages.xml import MapP, Trace
from tests.messages import assert_message_failure
from tests.messages.xml import assert_message


@pytest.mark.parametrize(("pid", "data"), [(42, "base64data")])
@pytest.mark.benchmark
def test_MapP(pid: int, data: str) -> None:
    xml_message = f"<ctl td='MapP' i='1245233875' pid='{pid}' p='{data}'/>"
    assert_message(
        MapP,
        xml_message,
        MinorMapEvent(index=pid, value=data),
    )


@pytest.mark.parametrize(
    "xml_message",
    sorted(
        {
            "<ctl td='MapP' i='1245233875' pid='XXX' p='base64data'/>",
            "<ctl td='MapP' i='1245233875' p='base64data'/>",
            "<ctl td='MapP' i='1245233875' pid='42' />",
            "<ctl td='MapP' i='1245233875' />",
        }
    ),
)
@pytest.mark.benchmark
def test_MapP_error(xml_message: str) -> None:
    assert_message_failure(MapP, xml_message, HandlingState.ANALYSE_LOGGED)


@pytest.mark.parametrize(("tf", "tt", "tr"), [(13, 42, "base64data")])
@pytest.mark.benchmark
def test_Trace(tf: int, tt: int, tr: str) -> None:
    xml_message = f"<ctl td='trace' trid='631369' tf='{tf}' tt='{tt}' tr='{tr}'/>"
    assert_message(
        Trace,
        xml_message,
        MapTraceEvent(start=tf, total=tt, data=tr),
    )


@pytest.mark.parametrize(
    "xml_message",
    sorted(
        {
            "<ctl td='trace' trid='631369' tt='17' tr='XQAABAAKAAAAAG0/wEAAA2cAS5AAAA=='/>",
            "<ctl td='trace' trid='631369' tf='XXX' tt='17' tr='XQAABAAKAAAAAG0/wEAAA2cAS5AAAA=='/>",
            "<ctl td='trace' trid='631369' tf='16' tr='XQAABAAKAAAAAG0/wEAAA2cAS5AAAA=='/>",
            "<ctl td='trace' trid='631369' tf='16' tt='XXX' tr='XQAABAAKAAAAAG0/wEAAA2cAS5AAAA=='/>",
            "<ctl td='trace' trid='631369' tf='16' tt='16' />",
            "<ctl td='trace' trid='631369' />",
        }
    ),
)
@pytest.mark.benchmark
def test_Trace_error(xml_message: str) -> None:
    assert_message_failure(Trace, xml_message, HandlingState.ANALYSE_LOGGED)
