from __future__ import annotations

import pytest

from deebot_client.events import MinorMapEvent
from deebot_client.message import HandlingState
from deebot_client.messages.xml import MapP
from tests.messages import assert_message, assert_message_failure


@pytest.mark.parametrize(("pid", "data"), [(42, "base64data")])
def test_MapP(pid: int, data: str) -> None:
    xml_message = f"<ctl td='MapP' i='1245233875' pid='{pid}' p='{data}'/>"
    assert_message(
        MapP,
        xml_message,
        MinorMapEvent(index=pid, value=data),
    )


@pytest.mark.parametrize(
    "xml_message",
    {
        "<ctl td='MapP' i='1245233875' pid='XXX' p='base64data'/>",
        "<ctl td='MapP' i='1245233875' p='base64data'/>",
        "<ctl td='MapP' i='1245233875' pid='42' />",
        "<ctl td='MapP' i='1245233875' />",
    },
)
def test_MapP_error(xml_message: str) -> None:
    assert_message_failure(MapP, xml_message, HandlingState.ANALYSE_LOGGED)
