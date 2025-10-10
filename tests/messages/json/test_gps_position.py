from __future__ import annotations

import pytest

from deebot_client.events import FirmwareEvent, GpsPositionEvent
from deebot_client.messages.json import OnGpsPos
from tests.messages.json import assert_message


@pytest.mark.parametrize(
    ("longitude", "latitude"),
    [
        ("-73.935242", "40.730610"),
        ("0.0", "0.0"),
        ("139.691706", "35.689487"),
    ],
)
async def test_onGpsPos(longitude: str, latitude: str) -> None:
    data = {
        "header": {
            "tzm": -240,
            "ts": "1759613597259855611",
            "fwVer": "1.13.31",
        },
        "body": {"data": {"longitude": longitude, "latitude": latitude}},
    }

    await assert_message(
        OnGpsPos,
        data,
        (FirmwareEvent("1.13.31"), GpsPositionEvent(float(longitude), float(latitude))),
    )
